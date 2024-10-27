

# build lambda via SAM
sam build
sam deploy --guided

# setup secrets
aws ssm put-parameter --name "restaurant/openai_api_key" --type "SecureString" --value "" --description "OpenAI API Key for Restaurant Order Processing"

# to trigger lambda execution
aws events put-events --entries '[{
  "Source": "com.restaurant.order",
  "DetailType": "NewOrder",
  "Detail": "{\"message\": \"I want to order peperoni pizza with extra cheese and pineapples\"}"
}]'


# ECR
aws ecr create-repository --repository-name react-food-order-app --region us-east-1

# create app runner service

aws iam create-role --role-name AppRunnerAccessRole --assume-role-policy-document file://app-runner-trust-policy.json
aws iam create-policy --policy-name AppRunnerAccessPolicy --policy-document file://ecr-access-policy.json
aws iam attach-role-policy --role-name AppRunnerAccessRole --policy-arn arn:aws:iam::{account}:policy/AppRunnerAccessPolicy

aws apprunner create-service --cli-input-json file://input.json --region us-east-1

#aws apprunner create-service \
#--service-name "food-service" \
#--source-configuration '{"ImageRepository": {"ImageIdentifier": "{account}.dkr.ecr.us-east-1.amazonaws.com/react-food-order-app:latest", "ImageRepositoryType": "ECR"}}' \
#--instance-configuration '{"Cpu": "1024", "Memory": "2048"}' \
#--authentication-configuration '{"AccessRoleArn": "arn:aws:iam::{account}:role/AppRunnerAccessRole"}' \
#--region "us-east-1"
#
#aws apprunner create-service \
#--service-name $SERVICE_NAME \
#--source-configuration '{"ImageRepository": {"ImageIdentifier": "'$REPOSITORY_URI:$IMAGE_TAG'", "ImageRepositoryType": "ECR"}}' \
#--instance-configuration '{"Cpu": "1024", "Memory": "2048"}' \
#--authentication-configuration '{"AccessRoleArn": "arn:aws:iam::'$(aws sts get-caller-identity --query Account --output text)':role/AppRunnerECRAccessRole"}' \
#--region "us-east-1"

# check status
aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:<your-aws-account-id>:service/$SERVICE_NAME/<service-id>

aws apprunner list-services --region $REGION

aws apprunner pause-service --service-arn <service-arn>

aws apprunner delete-service --service-arn <service-arn>
