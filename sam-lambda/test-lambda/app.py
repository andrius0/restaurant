import os
import json
import requests
from typing import TypedDict, Annotated, Sequence, List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ssm = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')

# Environment variables
OPENAI_API_KEY_PARAM_NAME = os.environ['OPENAI_API_KEY_PARAM_NAME']
USE_DYNAMODB = os.environ.get("USE_DYNAMODB", "True").lower() == "true"
SISTER_RESTAURANT_API_URL = os.environ.get("SISTER_RESTAURANT_API_URL", "http://sister-restaurant-api.example.com/inventory")
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

# DynamoDB setup
if USE_DYNAMODB:
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)

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
            logger.error(f"Error querying sister restaurant API: {response.status_code}")
            return {ingredient: False for ingredient in ingredients}
    except requests.RequestException as e:
        logger.error(f"Error querying sister restaurant API: {e}")
        return {ingredient: False for ingredient in ingredients}

def check_inventory(ingredients: List[str], inventory_choice: str) -> Dict[str, bool]:
    if inventory_choice == "current_restaurant":
        return check_inventory_dynamodb(ingredients) if USE_DYNAMODB else check_inventory_static(ingredients)
    elif inventory_choice == "sister_restaurant":
        return check_inventory_sister_restaurant(ingredients)
    else:
        logger.error(f"Invalid inventory choice: {inventory_choice}")
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

def lambda_handler(event, context):
    try:
        # Extract the message from the EventBridge event
        event_detail = event.get('detail', {})
        user_message = event_detail.get('message', '')

        logger.info(f"Received event: {json.dumps(event)}")
        logger.info(f"Processing user message: {user_message}")

        # Prepare the input for the workflow
        inputs = {
            "messages": [HumanMessage(content=user_message)],
            "order_intent": "",
            "ingredients": [],
            "food_type": ""
        }

        # Run the workflow
        result = None
        for output in app.stream(inputs):
            if "agent" in output:
                agent_output = output["agent"]
                if isinstance(agent_output, dict) and "messages" in agent_output:
                    last_message = agent_output["messages"][-1]
                    if isinstance(last_message, AIMessage):
                        result = last_message.content
            if "__end__" in output:
                break

        # Prepare the response
        if result:
            logger.info(f"Processing complete. Result: {result}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': result})
            }
        else:
            logger.error("No result generated")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'No result generated'})
            }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }