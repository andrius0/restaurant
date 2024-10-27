import boto3
import json
from botocore.exceptions import ClientError


def load_ingredients(table_name, ingredients):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    for ingredient in ingredients:
        try:
            table.put_item(
                Item={
                    'IngredientName': ingredient['name'],
                    'Quantity': ingredient['quantity']
                }
            )
            print(f"Added ingredient: {ingredient['name']}")
        except ClientError as e:
            print(f"Error adding ingredient {ingredient['name']}: {e.response['Error']['Message']}")


if __name__ == "__main__":
    # Read the Terraform output file
    try:
        with open('terraform.output.json', 'r') as f:
            outputs = json.load(f)
            table_name = outputs['dynamodb_table_name']['value']
    except FileNotFoundError:
        print("terraform.output.json not found. Using default table name.")
        table_name = "Ingredients"

    # Initial ingredients data
    ingredients = [
        {"name": "cheese", "quantity": 100},
        {"name": "tomato_sauce", "quantity": 80},
        {"name": "pepperoni", "quantity": 50},
        {"name": "mushrooms", "quantity": 40},
        {"name": "dough", "quantity": 150},
        {"name": "olives", "quantity": 30}
    ]

    load_ingredients(table_name, ingredients)