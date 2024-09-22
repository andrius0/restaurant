import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence, List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import boto3
from boto3.dynamodb.conditions import Attr
import json

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Feature flag to disable DynamoDB
USE_DYNAMODB = os.getenv("USE_DYNAMODB", "True").lower() == "true"


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    order_intent: Annotated[str, "The interpreted order intent"]
    ingredients: Annotated[List[str], "List of ingredients"]
    food_type: Annotated[str, "Type of food ordered"]


# Updated prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant for a restaurant. Interpret the user's food order, identifying the intent, ingredients, and type of food.
    Respond in the following JSON format:
    {{"intent": "order_food", "ingredients": ["ingredient1", "ingredient2"], "food_type": "type_of_food"}}
    """),
    MessagesPlaceholder(variable_name="messages"),
])

model = ChatOpenAI(api_key=openai_api_key)

if USE_DYNAMODB:
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Ingredients')


def check_inventory_dynamodb(ingredients: List[str]) -> Dict[str, bool]:
    inventory_status = {}
    for ingredient in ingredients:
        response = table.get_item(Key={'name': ingredient})
        inventory_status[ingredient] = 'Item' in response and response['Item']['in_stock']
    return inventory_status


def check_inventory_static(ingredients: List[str]) -> Dict[str, bool]:
    # Static inventory for demonstration
    static_inventory = {
        "pepperoni": True,
        "cheese": True,
        "dough": True,
        "tomato sauce": True,
        "mushrooms": False,
        "olives": True
    }
    return {ingredient: static_inventory.get(ingredient.lower(), False) for ingredient in ingredients}


def check_inventory(ingredients: List[str]) -> Dict[str, bool]:
    if USE_DYNAMODB:
        return check_inventory_dynamodb(ingredients)
    else:
        return check_inventory_static(ingredients)


def agent(state: AgentState):
    messages = state["messages"]
    response = model.invoke(prompt.invoke({"messages": messages}))

    try:
        parsed_response = json.loads(response.content)
    except json.JSONDecodeError:
        # Handle the case where the response is not valid JSON
        parsed_response = {
            "intent": "unknown",
            "ingredients": [],
            "food_type": "unknown"
        }

    inventory_status = check_inventory(parsed_response['ingredients'])

    result_message = f"Order intent: {parsed_response['intent']}\n"
    result_message += f"Food type: {parsed_response['food_type']}\n"
    result_message += "Ingredients availability:\n"
    for ingredient, available in inventory_status.items():
        result_message += f"- {ingredient}: {'Available' if available else 'Not available'}\n"

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
    "messages": [HumanMessage(content="I'd like to order a pepperoni pizza with extra cheese and mushrooms.")],
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