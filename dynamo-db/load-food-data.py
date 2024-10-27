import boto3

# Create a DynamoDB client
dynamodb = boto3.client('dynamodb', endpoint_url='http://localhost:8000')

# Define the table name
table_name = 'Ingredients'

# Create the table
try:
    response = dynamodb.create_table(
        TableName='Ingredients',
        AttributeDefinitions=[
            {
                'AttributeName': 'IngredientId',
                'AttributeType': 'S'
            },
        ],
        KeySchema=[
            {
                'AttributeName': 'IngredientId',
                'KeyType': 'HASH'
            },
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    print("Table created successfully!")
except Exception as e:
    print(f"Error creating table: {str(e)}")

# Initialize a session for DynamoDB Local or AWS environment
dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')


# Define a list of 20 common food items
common_food_items = [
    {"IngredientId": "1", "IngredientName": "apple", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-12-01"},
    {"IngredientId": "2", "IngredientName": "sugar", "Quantity": 100, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-01-01"},
    {"IngredientId": "3", "IngredientName": "water", "Quantity": 200, "UnitOfMeasurement": "liters", "ExpirationDate": "2025-12-31"},
    {"IngredientId": "4", "IngredientName": "flour", "Quantity": 75, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-02-28"},
    {"IngredientId": "5", "IngredientName": "salt", "Quantity": 60, "UnitOfMeasurement": "kg", "ExpirationDate": "2026-01-01"},
    {"IngredientId": "6", "IngredientName": "egg", "Quantity": 300, "UnitOfMeasurement": "pieces", "ExpirationDate": "2024-09-25"},
    {"IngredientId": "7", "IngredientName": "milk", "Quantity": 100, "UnitOfMeasurement": "liters", "ExpirationDate": "2024-10-10"},
    {"IngredientId": "8", "IngredientName": "butter", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-11-01"},
    {"IngredientId": "9", "IngredientName": "chicken Breast", "Quantity": 40, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-20"},
    {"IngredientId": "10", "IngredientName": "rice", "Quantity": 90, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-03-15"},
    {"IngredientId": "11", "IngredientName": "carrot", "Quantity": 60, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-09-30"},
    {"IngredientId": "12", "IngredientName": "tomato", "Quantity": 70, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-05"},
    {"IngredientId": "13", "IngredientName": "potato", "Quantity": 100, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-11-10"},
    {"IngredientId": "14", "IngredientName": "onion", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-15"},
    {"IngredientId": "15", "IngredientName": "broccoli", "Quantity": 20, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-01"},
    {"IngredientId": "16", "IngredientName": "cheese", "Quantity": 30, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-12-05"},
    {"IngredientId": "17", "IngredientName": "pasta", "Quantity": 80, "UnitOfMeasurement": "kg", "ExpirationDate": "2025-01-20"},
    {"IngredientId": "18", "IngredientName": "orange", "Quantity": 50, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-11-15"},
    {"IngredientId": "19", "IngredientName": "banana", "Quantity": 70, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-10-10"},
    {"IngredientId": "20", "IngredientName": "strawberry", "Quantity": 25, "UnitOfMeasurement": "kg", "ExpirationDate": "2024-09-25"},
    {"IngredientId": "21", "IngredientName": "dough", "Quantity": 25, "UnitOfMeasurement": "kg","ExpirationDate": "2024-09-25"},
    {"IngredientId": "22", "IngredientName": "tomato sauce", "Quantity": 25, "UnitOfMeasurement": "kg","ExpirationDate": "2024-09-25"},

]

# {'cheese': '0.3kg', 'dough': '0.5kg', 'tomato sauce': '0.2kg'}

# Reference the DynamoDB table
table = dynamodb.Table(table_name)

# Load each item into the table
for item in common_food_items:
    table.put_item(Item=item)

print("Successfully loaded 20 common food items into the DynamoDB table.")