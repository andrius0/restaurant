aws cloudformation create-stack --stack-name IngredientsStack --template-body file://ingredients-dynamodb.yml

## run local docker:
docker run -d -p 8000:8000 amazon/dynamodb-local

# list
aws dynamodb list-tables --endpoint-url http://localhost:8000

# list
aws dynamodb scan --table-name Ingredients --endpoint-url http://localhost:8000 --output json | jq

# describe
aws dynamodb describe-table --table-name Ingredients --query "Table.KeySchema" --endpoint-url http://localhost:8000

## read all items:
aws dynamodb scan --table-name Ingredients --endpoint-url http://localhost:8000

## query for items:
aws dynamodb query `
    --table-name Ingredients `
    --key-condition-expression "IngredientId = :ingredient_id" `
    --expression-attribute-values '{":ingredient_id": {"S": "1"}}' `
    --endpoint-url http://localhost:8000

## query for items:
aws dynamodb query `
    --table-name Ingredients `
    --key-condition-expression "IngredientId = :ingredient_id" `
    --expression-attribute-values '{":ingredient_id": {"S": "1"}}' `
    --endpoint-url http://localhost:8000

## with rest:
curl -X POST http://localhost:8000 \
-H "Content-Type: application/x-amz-json-1.0" \
-H "X-Amz-Target: DynamoDB_20120810.Scan" \
-d '{
    "TableName": "Ingredients"
}'

aws dynamodb put-item `
    --table-name Ingredients `
    --endpoint-url http://localhost:8000 `
    --item '{\"IngredientId\": {\"S\": \"22\"}, \"IngredientName\": {\"S\": \"tomato sauce\"}, \"Quantity\": {\"N\": \"25\"}, \"UnitOfMeasurement\": {\"S\": \"kg\"}, \"ExpirationDate\": {\"S\": \"2024-09-25\"}}'


aws dynamodb put-item `
    --table-name Ingredients `
    --endpoint-url http://localhost:8000 `
    --item '{\"IngredientId\": {\"S\": \"23\"}, \"IngredientName\": {\"S\": \"dough\"}, \"Quantity\": {\"N\": \"25\"}, \"UnitOfMeasurement\": {\"S\": \"kg\"}, \"ExpirationDate\": {\"S\": \"2024-09-25\"}}'

