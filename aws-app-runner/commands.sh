aws ecr create-repository --repository-name react-food-order-app --region <your-region>


aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.<your-region>.amazonaws.com


docker tag react-food-order-app:latest <your-aws-account-id>.dkr.ecr.<your-region>.amazonaws.com/react-food-order-app:latest
docker push <your-aws-account-id>.dkr.ecr.<your-region>.amazonaws.com/react-food-order-app:latest


REPOSITORY_URI=<your-aws-account-id>.dkr.ecr.<your-region>.amazonaws.com/react-food-order-app
IMAGE_TAG=latest
SERVICE_NAME=react-food-order-app-runner
REGION=<your-region>

# create app runner service
aws apprunner create-service \
--service-name $SERVICE_NAME \
--source-configuration ImageRepository={"ImageIdentifier=$REPOSITORY_URI:$IMAGE_TAG","ImageRepositoryType=ECR"} \
--instance-configuration Cpu="1024",Memory="2048" \
--region $REGION

# check status
aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:<your-aws-account-id>:service/$SERVICE_NAME/<service-id>

aws apprunner list-services --region $REGION

aws apprunner pause-service --service-arn <service-arn>

aws apprunner delete-service --service-arn <service-arn>

# create passwords
aws ssm put-parameter --name "/restaurant/openai_api_key" --type "SecureString" --value "<>" --description "OpenAI API Key for Restaurant Order Processing"