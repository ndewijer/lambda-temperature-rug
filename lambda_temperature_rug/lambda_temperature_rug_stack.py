from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    Duration,
    CfnOutput
)
from constructs import Construct

class LambdaTemperatureRugStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Parameters
        application_id = self.node.try_get_context("application_id") or "temperature-rug"
        stage = self.node.try_get_context("stage") or "dev"
    
        # Define Lambda function
        temperature_rug_lambda = _lambda.DockerImageFunction(
            self, 'TemperatureRugLambda',
            function_name=f"{application_id}-{stage}",
            code=_lambda.DockerImageCode.from_image_asset('lambda'),
            memory_size=128,
            timeout=Duration.seconds(15),
            architecture=_lambda.Architecture.ARM_64,
        )
        
        # Add managed policy
        temperature_rug_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        lambdaURL = temperature_rug_lambda.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE
        )

        CfnOutput(self, "LambdaURL",
            value=lambdaURL.url,
            description="Lambda URL"
        )