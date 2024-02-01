""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import boto3
import constants
import aws_cdk as cdk

from aws_cdk import (
    aws_s3 as _s3,
    aws_ssm as _ssm
)
from typing import Dict
from constructs import Construct
from components.text_api import TextApi
from components.rag_api import RagApi
from components.vector_store import VectorStore

class InfrastructureStack(cdk.Stack):

    def __init__(self, scope: Construct, id: str, *, model_parameter_name: str=None, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)

        # Load pipeline variables form toolchain context
        context = self.node.try_get_context("toolchain-context")

        # Define the Bedrock Text API
        text_api = TextApi(self, "TextAPI")
        text_api.text_handler.add_environment(
            key="TEXT_MODEL_ID",
            value=InfrastructureStack._get_model(
                parameter_name=model_parameter_name,
                region=constants.REGION,
                context=context
            )
        )

        # Expose the Text API Endpoint for system testing
        self.text_apigw_output = cdk.CfnOutput(
            self,
            "TextApiEndpointUrl",
            value=text_api.text_apigw.url
        )

        # Define the S3 Bucket for RAG data
        # NOTE: An S3 bucket will be created for both the `QA` and `PROD` stages
        rag_bucket = _s3.Bucket(
            self,
            "RagDataBucket",
            bucket_name=f"{self.stack_name.lower()}-{cdk.Aws.REGION}-{cdk.Aws.ACCOUNT_ID}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True
        )

        # Define the Bedrock Text API for RAG
        rag_api = RagApi(self, "RagAPI")
        rag_api.rag_handler.add_environment(key="TEXT_MODEL_ID", value=context.get("bedrock-text-model-id"))
        rag_api.rag_handler.add_environment(key="EMBEDDING_MODEL_ID", value=context.get("bedrock-embedding-model-id"))

        # Expose RAG API endpoint for cross-stack, and external app reference
        _ssm.StringParameter(
            self,
            "RagEndpointParameter",
            parameter_name=f"{self.stack_name}-RagEndpointParameter",
            string_value=rag_api.rag_apigw.url
        )

        # Add the OpenSearch Vector Store
        vector_store = VectorStore(self, "VectorStore", data_bucket=rag_bucket)

        # Apply Vector Store integration with RAG API
        rag_api.rag_handler.add_environment(key="OPENSEARCH_INDEX", value=context.get("embedding-index-name"))
        rag_api.rag_handler.add_environment(key="OPENSEARCH_ENDPOINT", value=vector_store.endpoint_name)
        rag_api.rag_handler.add_environment(key="OPENSEARCH_SECRET", value=vector_store.opensearch_secret.secret_name)

        # Give the TEXT API handler access to the OpenSearch master use secret, for authentication
        vector_store.opensearch_secret.grant_read(rag_api.rag_handler)

        # Expose the RAG API Endpoint for system testing
        self.rag_apigw_output = cdk.CfnOutput(
            self,
            "RagApiEndpointUrl",
            value=rag_api.rag_apigw.url
        )


    @staticmethod
    def _get_model(parameter_name: str, region: str, context: Dict) -> str:
        # Return the model context if deploying the infrastructure in DEV/TEST
        if parameter_name == None:
            return context.get("bedrock-text-model-id")

        # Return the model context within the CI/CD/CT toolchain
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            response = ssm_client.get_parameter(
                Name=parameter_name
            )
            model = response["Parameter"]["Value"]
            if model == "PLACEHOLDER":
                # There is no custom model, therefore return context default
                return context.get("bedrock-text-model-id")
            else:
                # Custom tuned model exists from continuous tuning stack
                return model
        except ssm_client.exceptions.ParameterNotFound:
            # The model parameter doesn't exist, meaning the Infrastructure stack has not been
            # deployed within the context of the CI/CD/CT toolchain
            return context.get("bedrock-text-model-id")
