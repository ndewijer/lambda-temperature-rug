import aws_cdk as core
import aws_cdk.assertions as assertions

from lambda_temperature_rug.lambda_temperature_rug_stack import LambdaTemperatureRugStack

# example tests. To run these tests, uncomment this file along with the example
# resource in lambda_temperature_rug/lambda_temperature_rug_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = LambdaTemperatureRugStack(app, "lambda-temperature-rug")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
