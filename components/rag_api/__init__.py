""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import aws_cdk as cdk

from aws_cdk import (
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_apigateway as _apigw
)
from constructs import Construct

class RagApi(Construct):

    def __init__(self, scope: Construct, id: str) -> None:

        super().__init__(scope, id)

        # Define the IAM Role for Lambda to invoke the Bedrock service
        role = _iam.Role(
            self,
            "RagHandlerRole",
            assumed_by=_iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ]
        )
        role.attach_inline_policy(
            _iam.Policy(
                self,
                "RagInvokePolicy",
                statements=[
                    _iam.PolicyStatement(
                        actions=[
                            "bedrock:InvokeModel"
                        ],
                        effect=_iam.Effect.ALLOW,
                        resources=["*"]
                    )
                ]
            )
        )

        # Create Lambda Functions for the text2text API
        self.rag_handler = _lambda.Function(
            self,
            "RagHandler",
            code=_lambda.Code.from_asset(
                path="components/rag_api/runtime",
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",
            role=role,
            memory_size=512,
            timeout=cdk.Duration.seconds(300)
        )

        # Create the API Gateway
        self.rag_apigw = _apigw.LambdaRestApi(
            self,
            "RagApiGateway",
            handler=self.rag_handler
        )
