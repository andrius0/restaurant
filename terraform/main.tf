terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Lambda function
resource "aws_lambda_function" "restaurant_order" {
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  function_name    = "restaurant-order-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      OPENAI_API_KEY_PARAM_NAME = aws_ssm_parameter.openai_api_key.name
      DYNAMODB_TABLE_NAME       = aws_dynamodb_table.ingredients.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}

# Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"
  source_dir  = "${path.module}/lambda"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/restaurant-order-processor"
  retention_in_days = 14
}

# DynamoDB table
resource "aws_dynamodb_table" "ingredients" {
  name           = "Ingredients"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "IngredientName"
  stream_enabled = true

  attribute {
    name = "IngredientName"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Project     = "Restaurant-Order-System"
  }
}

# SSM Parameter for OpenAI API Key
resource "aws_ssm_parameter" "openai_api_key" {
  name        = "/restaurant/openai-api-key"
  description = "OpenAI API Key for restaurant order processing"
  type        = "SecureString"
  value       = var.openai_api_key

  tags = {
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "restaurant_order_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "restaurant_order_lambda_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.ingredients.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = aws_ssm_parameter.openai_api_key.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# API Gateway
resource "aws_apigatewayv2_api" "lambda" {
  name          = "restaurant_order_api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "lambda" {
  api_id = aws_apigatewayv2_api.lambda.id

  name        = "prod"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp               = "$context.identity.sourceIp"
      requestTime            = "$context.requestTime"
      protocol               = "$context.protocol"
      httpMethod             = "$context.httpMethod"
      resourcePath           = "$context.resourcePath"
      routeKey               = "$context.routeKey"
      status                 = "$context.status"
      responseLength         = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
}

resource "aws_apigatewayv2_integration" "restaurant_order" {
  api_id = aws_apigatewayv2_api.lambda.id

  integration_uri    = aws_lambda_function.restaurant_order.invoke_arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "restaurant_order" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "POST /order"
  target    = "integrations/${aws_apigatewayv2_integration.restaurant_order.id}"
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name = "/aws/api_gw/${aws_apigatewayv2_api.lambda.name}"

  retention_in_days = 14
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restaurant_order.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.lambda.execution_arn}/*/*"
}