#!/usr/bin/env python3
import boto3
import constants
import aws_cdk as cdk

from stacks.infrastructure import InfrastructureStack
from stacks.toolchain import ToolChainStack

app = cdk.App()

# The following CloudFormation Stack is used for a stand-alone development of the generative AI application, i.e. no CI/CD/CT Pipeline automation
# InfrastructureStack(
#     app,
#     f"{constants.WORKLOAD_NAME}-DEV",
#     env=cdk.Environment(
#         account=boto3.client("sts").get_caller_identity().get("Account"),
#         region=constants.REGION
#     )
# )

# The following Cloudformation Stack defines the self-updating CDK Pipeline (i.e. CI/CD/CT Pipeline) for QA/PROD/TUNING deployment
ToolChainStack(
    app,
    f"{constants.WORKLOAD_NAME}-Toolchain",
    env=cdk.Environment(
        account=boto3.client("sts").get_caller_identity().get("Account"),
        region=constants.REGION
    )
)

app.synth()
