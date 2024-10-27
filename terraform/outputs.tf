output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.restaurant_order.function_name
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.ingredients.name
}

output "api_endpoint" {
  description = "HTTP API Gateway endpoint"
  value       = aws_apigatewayv2_api.lambda.api_endpoint
}

output "api_stage_url" {
  description = "Complete API Gateway stage URL"
  value       = "${aws_apigatewayv2_api.lambda.api_endpoint}/prod"
}