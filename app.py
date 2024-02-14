#!/usr/bin/env python3
import boto3
import constants
import aws_cdk as cdk

from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks
from stacks.infrastructure import InfrastructureStack
from stacks.toolchain import ToolChainStack

app = cdk.App()

# The following CloudFormation Stack is used for a stand-alone development of the generative AI application, i.e. no CI/CD/CT Pipeline automation
# InfrastructureStack(
#     app,
#     f"{constants.WORKLOAD_NAME}-DEV",
#     description="Guidance for Dynamic Non-Player Character (NPC) Dialogue on AWS (SO9327)",
#     env=cdk.Environment(
#         account=boto3.client("sts").get_caller_identity().get("Account"),
#         region=constants.REGION
#     )
# )

# The following Cloudformation Stack defines the self-updating CDK Pipeline (i.e. CI/CD/CT Pipeline) for QA/PROD/TUNING deployment
ToolChainStack(
    app,
    f"{constants.WORKLOAD_NAME}-Toolchain",
    description="Guidance for Dynamic Non-Player Character (NPC) Dialogue on AWS (SO9327)",
    env=cdk.Environment(
        account=boto3.client("sts").get_caller_identity().get("Account"),
        region=constants.REGION
    )
)

# Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
