#!/usr/bin/env python3
import os

import aws_cdk as cdk

from lambda_temperature_rug.lambda_temperature_rug_stack import LambdaTemperatureRugStack


app = cdk.App()
LambdaTemperatureRugStack(app, "LambdaTemperatureRugStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION') or 'eu-west-1'
    )
)

app.synth()
