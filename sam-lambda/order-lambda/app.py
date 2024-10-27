from typing import TypedDict, Literal, Optional, List, Dict
from datetime import datetime
from IPython.display import Image
from botocore.exceptions import ClientError
from langgraph.graph import StateGraph, START, END
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from uuid import uuid4
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import json
import logging
from boto3.dynamodb.conditions import Attr
import boto3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment vars
load_dotenv()

# Environment variables
OPENAI_API_KEY_PARAM_NAME = os.environ['OPENAI_API_KEY_PARAM_NAME']
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'Ingredients')


# Retrieve OpenAI API key from SSM Parameter Store
def get_ssm_parameter(param_name):
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Error retrieving SSM parameter: {str(e)}")
        raise

openai_api_key = get_ssm_parameter(OPENAI_API_KEY_PARAM_NAME)

# Initialize AWS clients
ssm = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table(DYNAMODB_TABLE_NAME)


# Define the state type
class PizzaOrderState(TypedDict):
    # Order details
    order_id: str
    order_status: Literal['initiated', 'ingredients_checked', 'submitted', 'type_decided', 'completed']
    order_type: Optional[Literal['pickup', 'delivery']]

    # Order interpretation
    intent: str
    food_type: str
    required_ingredients: Dict[str, float]  # ingredient name to weight in kg
    inventory_choice: Literal['current_restaurant', 'sister_restaurant']

    # Inventory and availability
    ingredients_available: bool
    missing_ingredients: list[str]

    # Timing
    order_time: datetime
    estimated_pickup_time: Optional[datetime]
    estimated_delivery_time: Optional[datetime]

    # Customer info
    customer_name: str
    delivery_address: Optional[str]
    phone_number: str
    customer_message: str  # Store the original customer message

    # Order details
    items: list[dict]
    total_price: float

    # Processing metadata
    errors: list[str]
    notes: list[str]
    messages: List[dict]  # Store conversation history

# State processing functions
def interpret_order(state: PizzaOrderState) -> PizzaOrderState:
    """Process the customer's order using the chat prompt."""
    # Generate order ID if not present
    if not state['order_id']:
        state['order_id'] = str(uuid4())

    # Add the customer message to the messages history
    if 'messages' not in state:
        state['messages'] = []

    state['messages'].append({"role": "user", "content": state['customer_message']})

    try:
        # Direct invocation of prompt and model
        response = model.invoke(prompt.invoke({"messages": state['messages']}))

        # Parse the response (assuming it returns JSON string)
        parsed_response = json.loads(response.content)

        # Update state with parsed response
        state['intent'] = parsed_response['intent']
        state['food_type'] = parsed_response['food_type']
        state['required_ingredients'] = parsed_response['ingredients']
        state['inventory_choice'] = parsed_response['inventory_choice']

        state['order_status'] = 'initiated'
        state['order_time'] = datetime.now()

        # Add processing note
        state['notes'].append(f"Order interpreted at {datetime.now()}")

    except json.JSONDecodeError as e:
        state['errors'].append(f"Error parsing LLM response: {str(e)}")
        state['notes'].append("Failed to parse LLM response")
    except Exception as e:
        state['errors'].append(f"Error interpreting order: {str(e)}")
        state['notes'].append(f"Failed to interpret order at {datetime.now()}")

    return state


def convert_kg_to_float(value_str):
    """
    Convert a string with format '<number>kg' to float

    Args:
        value_str (str): String in format like '0.1kg' or '4kg'

    Returns:
        float: Numerical value without 'kg'

    Raises:
        ValueError: If string is not in correct format
    """
    # Remove 'kg' and any whitespace
    try:
        # Remove 'kg' from the end and convert to float
        number_str = value_str.lower().replace('kg', '').strip()
        return float(number_str)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid format: {value_str}. Expected format: '<number>kg'")


def can_make_meal(available_ingredients, required_ingredients):
    """
    Check if we can make a meal based on available and required ingredients.

    Args:
        available_ingredients: List of dicts with 'ingredient' and 'quantity' keys
        required_ingredients: Dict with ingredient names as keys and required quantities as values

    Returns:
        tuple: (bool, str) - (True/False if meal can be made, explanation message)
    """
    # Convert available ingredients to a more convenient format
    available_dict = {item['ingredient']: item['quantity'] for item in available_ingredients}

    # Check if we have all required ingredients
    for ingredient, required_amount in required_ingredients.items():
        # Check if ingredient exists in available ingredients
        if ingredient not in available_dict:
            return False, f"Missing ingredient: {ingredient}"

        # Convert required amount to float
        required_amount = convert_kg_to_float(required_amount)

        # Check if we have enough quantity
        available_amount = available_dict[ingredient]

        missing_ingredients = []

        # If quantity is None, we assume it's a boolean ingredient (just needs to be present)
        if available_amount is None:
            missing_ingredients.append(ingredient)
            return False, missing_ingredients

        if available_amount < required_amount:
            missing_ingredients.append(ingredient)
            return False, missing_ingredients

    return True, "All ingredients available in sufficient quantities"


def check_ingredients(state: PizzaOrderState) -> PizzaOrderState:
    """Check if all required ingredients are available in the chosen inventory."""
    state['order_status'] = 'ingredients_checked'

    inventory_available = check_inventory_dynamodb(list(state['required_ingredients'].keys()))

    required_ingredients = state['required_ingredients']

    can_make = can_make_meal(inventory_available, required_ingredients)

    if can_make[0]:
        state['ingredients_available'] = True
        state['missing_ingredients'] = []
    else:
        state['ingredients_available'] = False
        state['missing_ingredients'] = can_make[1]
    # inventory available from DB

    return state


def submit_order(state: PizzaOrderState) -> PizzaOrderState:
    """Process the order submission."""
    if not state['ingredients_available']:
        state['errors'].append("Cannot submit order: missing ingredients")
        return state

    state['order_status'] = 'submitted'

    # Calculate total price (mock calculation)
    base_price = 10.0  # TODO:  Base price for any order
    float_list = [float(x) for x in list(state['required_ingredients'].values())]

    # TODO: this is wrong, but ok
    ingredient_cost = sum(0.5 * amount for amount in float_list)

    state['total_price'] = base_price + ingredient_cost

    # Add processing note
    state['notes'].append(f"Order submitted with total price: ${state['total_price']:.2f}")

    return state


def decide_order_type(state: PizzaOrderState) -> PizzaOrderState:
    """Determine if the order is for pickup or delivery."""
    state['order_status'] = 'type_decided'

    # Determine order type based on delivery address presence
    # if state.get('delivery_address'):
    if False:
        state['order_type'] = 'delivery'
        state['notes'].append("Order type set to delivery")
    else:
        state['order_type'] = 'pickup'
        state['notes'].append("Order type set to pickup")

    return state


def calculate_pickup_time(state: PizzaOrderState) -> PizzaOrderState:
    """Calculate estimated pickup time."""
    if state['order_type'] != 'pickup':
        return state

    # Mock time calculation: current time + 30 minutes
    pickup_time = datetime.now()
    pickup_time = pickup_time.replace(minute=pickup_time.minute + 30)
    state['estimated_pickup_time'] = pickup_time

    state['notes'].append(f"Estimated pickup time set to: {pickup_time}")

    print("send message here")

    return state


def process_pickup_order(state: PizzaOrderState) -> PizzaOrderState:
    """Handle pickup-specific processing."""
    state['order_status'] = 'completed'

    # Add processing notes
    state['notes'].append(
        f"Pickup order processed. Ready for pickup at: {state['estimated_pickup_time']}"
    )
    return state


def process_delivery_order(state: PizzaOrderState) -> PizzaOrderState:
    """Handle delivery-specific processing."""
    state['order_status'] = 'completed'

    # Mock delivery time calculation: current time + 45 minutes
    delivery_time = datetime.now()
    delivery_time = delivery_time.replace(minute=delivery_time.minute + 45)
    state['estimated_delivery_time'] = delivery_time

    # Add processing notes
    state['notes'].append(
        f"Delivery order processed. Estimated delivery time: {state['estimated_delivery_time']}"
    )
    return state


# Routing functions
def route_after_ingredients_check(state: PizzaOrderState) -> str:
    """Determine next state after ingredients check."""
    return "submit_order" if state['ingredients_available'] else END


def route_after_order_type(state: PizzaOrderState) -> str:
    """Determine next state based on order type."""
    return "pickup_order" if state['order_type'] == 'pickup' else "delivery_order"


def check_ingredient_quantity_by_name(ingredient_name):
    try:
        filter_expression = Attr('IngredientName').eq(ingredient_name)
        logger.info(f"Scanning table for ingredient: {ingredient_name}")
        response = table.scan(FilterExpression=filter_expression)

        if response['Count'] == 0:
            logger.warning(f"Ingredient '{ingredient_name}' not found.")
            return None

        item = response['Items'][0]
        quantity = int(item.get('Quantity', 0))

        if quantity > 0:
            logger.info(f"Ingredient '{ingredient_name}' found. Quantity: {quantity}")
            return quantity
        else:
            logger.warning(f"Ingredient '{ingredient_name}' found, but quantity is 0.")
            return None

    except ClientError as e:
        logger.error(f"An error occurred: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return None


def check_inventory_dynamodb(ingredients: List[str]) -> list[dict[str, str | None | int]]:
    recipe_ingredients = []
    for ingredient in ingredients:
        quantity = check_ingredient_quantity_by_name(ingredient)
        inventory_status = {'ingredient': ingredient, 'quantity': quantity}
        recipe_ingredients.append(inventory_status)
    return recipe_ingredients

def check_inventory_sister_restaurant(ingredients):
    return False

# Example initial state
def create_initial_state(customer_message: str) -> PizzaOrderState:
    return {
        "order_id": "",
        "order_status": "initiated",
        "order_type": None,
        "intent": "",
        "food_type": "",
        "required_ingredients": {},
        "inventory_choice": "current_restaurant",
        "ingredients_available": False,
        "missing_ingredients": [],
        "order_time": datetime.now(),
        "estimated_pickup_time": None,
        "estimated_delivery_time": None,
        "customer_name": "",
        "delivery_address": None,
        "phone_number": "",
        "customer_message": customer_message,
        "items": [],
        "total_price": 0.0,
        "errors": [],
        "notes": [],
        "messages": []
    }


# Create the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant for a restaurant. Interpret the user's food order, identifying the intent, ingredients, and type of food. 
    After identifying food provide generic amounts of ingredients required in kilograms. 
    Respond in the following JSON format:
    {{"intent": "order_food", "ingredients": ["ingredient1": "weight1", "ingredient2": "weight2"], "food_type": "type_of_food"}}
    After analyzing the order, decide which inventory to check:
    - If the order is for pizza or pasta, use the "current_restaurant" inventory.
    - For all other food types, use the "sister_restaurant" inventory.
    Include your decision in the JSON response as "inventory_choice": "current_restaurant" or "inventory_choice": "sister_restaurant".
    """),
    MessagesPlaceholder(variable_name="messages"),
])

model = ChatOpenAI(api_key=openai_api_key)

# Build the graph
builder = StateGraph(PizzaOrderState)

# Add nodes
builder.add_node("interpret_order", interpret_order)
builder.add_node("check_ingredients", check_ingredients)
builder.add_node("submit_order", submit_order)
builder.add_node("decide_order_type", decide_order_type)
builder.add_node("calculate_pickup_time", calculate_pickup_time)
builder.add_node("pickup_order", process_pickup_order)
builder.add_node("delivery_order", process_delivery_order)

# Add edges
builder.add_edge(START, "interpret_order")
builder.add_edge("interpret_order", "check_ingredients")

builder.add_conditional_edges(
    "check_ingredients",
    route_after_ingredients_check
)

builder.add_edge("submit_order", "decide_order_type")

builder.add_conditional_edges(
    "decide_order_type",
    route_after_order_type
)

builder.add_edge("pickup_order", "calculate_pickup_time")
builder.add_edge("calculate_pickup_time", END)
builder.add_edge("delivery_order", END)

# Compile the graph
graph = builder.compile()

# Save the graph visualization
img = graph.get_graph().draw_mermaid_png()
with open("restaurant_order_flow.png", "wb") as f:
    f.write(img)


def lambda_handler(event, context):
    try:
        # Parse the incoming event
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})

        # Create initial state
        initial_state = create_initial_state(body)

        # Process the order through the graph
        final_state = graph.invoke(initial_state)

        # Prepare the response
        response = {
            "order_id": final_state['order_id'],
            "status": final_state['order_status'],
            "total_price": final_state['total_price'],
            "notes": final_state['notes'],
            "errors": final_state['errors']
        }

        # Add delivery/pickup specific information
        if final_state['order_type'] == 'pickup':
            response['estimated_pickup_time'] = final_state['estimated_pickup_time'].isoformat() if final_state[
                'estimated_pickup_time'] else None
        else:
            response['estimated_delivery_time'] = final_state['estimated_delivery_time'].isoformat() if final_state[
                'estimated_delivery_time'] else None

        return {
            "statusCode": 200,
            "body": json.dumps(response),
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except Exception as e:
        logger.error(f"Error processing order: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            }),
            "headers": {
                "Content-Type": "application/json"
            }
        }