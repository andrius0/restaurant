import boto3

# Initialize a session for DynamoDB Local or AWS environment
dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

# Define the table name
table_name = 'Ingredients'

# Define a list of 20 common food items
common_food_items = [
    {"IngredientId": "1", "IngredientName": "Apple", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-12-01"},
    {"IngredientId": "2", "IngredientName": "Sugar", "Quantity": 100, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-01-01"},
    {"IngredientId": "3", "IngredientName": "Water", "Quantity": 200, "UnitOfMeasurement": "liters", "ExpirationDate": "2025-12-31"},
    {"IngredientId": "4", "IngredientName": "Flour", "Quantity": 75, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-02-28"},
    {"IngredientId": "5", "IngredientName": "Salt", "Quantity": 60, "UnitOfMeasurement": "kg", "ExpirationDate": "2026-01-01"},
    {"IngredientId": "6", "IngredientName": "Egg", "Quantity": 300, "UnitOfMeasurement": "pieces", "ExpirationDate": "2024-09-25"},
    {"IngredientId": "7", "IngredientName": "Milk", "Quantity": 100, "UnitOfMeasurement": "liters", "ExpirationDate": "2024-10-10"},
    {"IngredientId": "8", "IngredientName": "Butter", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-11-01"},
    {"IngredientId": "9", "IngredientName": "Chicken Breast", "Quantity": 40, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-20"},
    {"IngredientId": "10", "IngredientName": "Rice", "Quantity": 90, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-03-15"},
    {"IngredientId": "11", "IngredientName": "Carrot", "Quantity": 60, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-09-30"},
    {"IngredientId": "12", "IngredientName": "Tomato", "Quantity": 70, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-05"},
    {"IngredientId": "13", "IngredientName": "Potato", "Quantity": 100, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-11-10"},
    {"IngredientId": "14", "IngredientName": "Onion", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-15"},
    {"IngredientId": "15", "IngredientName": "Broccoli", "Quantity": 20, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-01"},
    {"IngredientId": "16", "IngredientName": "Cheese", "Quantity": 30, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-12-05"},
    {"IngredientId": "17", "IngredientName": "Pasta", "Quantity": 80, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-01-20"},
    {"IngredientId": "18", "IngredientName": "Orange", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-11-15"},
    {"IngredientId": "19", "IngredientName": "Banana", "Quantity": 70, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-10"},
    {"IngredientId": "20", "IngredientName": "Strawberry", "Quantity": 25, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-09-25"}
]

# Reference the DynamoDB table
table = dynamodb.Table(table_name)

# Load each item into the table
for item in common_food_items:
    table.put_item(Item=item)

print("Successfully loaded 20 common food items into the DynamoDB table.")