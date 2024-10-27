variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "initial_ingredients" {
  description = "Initial ingredients to load into DynamoDB"
  type = list(object({
    name     = string
    quantity = number
  }))
  default = [
    {
      name     = "cheese"
      quantity = 100
    },
    {
      name     = "tomato_sauce"
      quantity = 80
    },
    {
      name     = "pepperoni"
      quantity = 50
    },
    {
      name     = "mushrooms"
      quantity = 40
    },
    {
      name     = "dough"
      quantity = 150
    },
    {
      name     = "olives"
      quantity = 30
    }
  ]
}