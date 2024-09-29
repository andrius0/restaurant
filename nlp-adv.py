import os
import json
import requests
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence, List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
USE_DYNAMODB = os.getenv("USE_DYNAMODB", "True").lower() == "true"
SISTER_RESTAURANT_API_URL = os.getenv("SISTER_RESTAURANT_API_URL", "http://sister-restaurant-api.example.com/inventory")


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    order_intent: Annotated[str, "The interpreted order intent"]
    ingredients: Annotated[List[str], "List of ingredients"]
    food_type: Annotated[str, "Type of food ordered"]


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

if USE_DYNAMODB:
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
    table = dynamodb.Table('Ingredients')


def check_ingredient_quantity_by_name(ingredient_name):
    try:
        # Create the filter expression
        filter_expression = boto3.dynamodb.conditions.Attr('IngredientName').eq(ingredient_name)
        logger.info(f"Filter expression: {filter_expression}")

        # Perform the scan operation
        logger.info(f"Scanning table for ingredient: {ingredient_name}")
        response = table.scan(FilterExpression=filter_expression)

        # Log the response
        logger.info(f"Scan response: {response}")

        # Check if any items were found
        if response['Count'] == 0:
            logger.warning(f"Ingredient '{ingredient_name}' not found.")
            return None

        # Get the first matching item (assuming ingredient names are unique)
        item = response['Items'][0]
        logger.info(f"Found item: {item}")

        # Get the quantity
        quantity = int(item.get('Quantity', 0))
        logger.info(f"Quantity: {quantity}")

        # Check if the quantity is greater than 0
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


def check_inventory_static(ingredients: List[str]) -> Dict[str, bool]:
    static_inventory = {
        "pepperoni": True, "cheese": True, "dough": True,
        "tomato sauce": True, "mushrooms": False, "olives": True
    }
    return {ingredient: static_inventory.get(ingredient.lower(), False) for ingredient in ingredients}


def check_inventory_sister_restaurant(ingredients: List[str]) -> Dict[str, bool]:
    try:
        response = requests.post(SISTER_RESTAURANT_API_URL, json={"ingredients": ingredients})
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error querying sister restaurant API: {response.status_code}")
            return {ingredient: False for ingredient in ingredients}
    except requests.RequestException as e:
        print(f"Error querying sister restaurant API: {e}")
        return {ingredient: False for ingredient in ingredients}


def check_inventory(ingredients: List[str], inventory_choice: str) -> Dict[str, bool]:
    # LLM decides if it's current restaurant or if it's something else
    if inventory_choice == "current_restaurant":
        return check_inventory_dynamodb(ingredients) if USE_DYNAMODB else check_inventory_static(ingredients)
    elif inventory_choice == "sister_restaurant":
        return check_inventory_sister_restaurant(ingredients)
    else:
        print(f"Invalid inventory choice: {inventory_choice}")
        return {ingredient: False for ingredient in ingredients}


def agent(state: AgentState):
    messages = state["messages"]
    response = model.invoke(prompt.invoke({"messages": messages}))

    try:
        parsed_response = json.loads(response.content)
    except json.JSONDecodeError:
        parsed_response = {
            "intent": "unknown",
            "ingredients": [],
            "food_type": "unknown",
            "inventory_choice": "current_restaurant"
        }

    inventory_status = check_inventory(parsed_response['ingredients'],
                                       parsed_response.get('inventory_choice', 'current_restaurant'))

    result_message = f"Order intent: {parsed_response['intent']}\n"
    result_message += f"Food type: {parsed_response['food_type']}\n"
    result_message += f"Inventory checked: {parsed_response.get('inventory_choice', 'current_restaurant')}\n"
    result_message += "Ingredients availability:\n"

    for item in inventory_status:
        ingredient = item["ingredient"]
        amount_remaining = item['quantity']
        result_message += f"- {ingredient}: amount remaining: {amount_remaining}\n"

    return {
        "messages": messages + [AIMessage(content=result_message)],
        "order_intent": parsed_response['intent'],
        "ingredients": parsed_response['ingredients'],
        "food_type": parsed_response['food_type']
    }


workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app = workflow.compile()

# Example usage
inputs = {
    "messages": [HumanMessage(content="I'd like to order chocolate chip cookies and milk.")],
    "order_intent": "",
    "ingredients": [],
    "food_type": ""
}

for output in app.stream(inputs):
    if "agent" in output:
        agent_output = output["agent"]
        if isinstance(agent_output, dict) and "messages" in agent_output:
            last_message = agent_output["messages"][-1]
            if isinstance(last_message, AIMessage):
                print(f"Agent: {last_message.content}")
    if "__end__" in output:
        break