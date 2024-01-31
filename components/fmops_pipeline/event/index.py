""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import boto3
import json

from typing import Any
from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Logger

# Global parameters
tracer = Tracer()
logger = Logger()


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    # NOTE: The following code requires provisioned thorughput to be purchased,
    # and configured for the Bedrock custom model before it invoked by the text
    # and RAG APIs.
    # See https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    logger.info("Getting Provisioned Throughput model ARN ...")
    model_id = get_model_arn(
        model_name=event["detail"]["CustomerMetadataProperties"]["ModelName"]
    )
    logger.info(f"Provisioned Throughput model: {model_id}")
    update_parameter(
        parameter_name=os.environ["MODEL_PARAMETER"],
        model_name=model_id
    )
    logger.info("Executing release change of CI/CD Pipeline ...")
    pipeline_execution_id = start_pipeline(
        name=os.environ["PIPELINE_NAME"]
    )
    return {
        "statusCode": 200,
        "body": pipeline_execution_id
    }


def get_model_arn(model_name: str) -> str:
    bedrock_client = boto3.client("bedrock")
    try:
        # Get the custom model details for the approved custom model
        custom_model = bedrock_client.list_custom_models(
            nameContains=model_name
        )
        # Get the provisioned throughput resource for the `custom_model`
        provisioned_models = bedrock_client.list_provisioned_model_throughputs(
            statusEquals="InService",
            sortBy="CreationTime",
            sortOrder="Descending"
        )
        # Return the ARN for the provisioned model as the new model ID for inference
        for model in provisioned_models["provisionedModelSummaries"]:
            if model["modelArn"] == custom_model["modelSummaries"][0]["modelArn"]:
                return model["provisionedModelArn"]

    except ClientError as e:
        raise Exception(e.response["Error"]["Message"])


def update_parameter(parameter_name: str, model_name: str) -> Any:
    logger.info("Updating SSM Parameter with new model custom model name ...")
    ssm_client = boto3.client("ssm")
    try:
        ssm_client.put_parameter(
            Name=parameter_name,
            Value=model_name,
            Overwrite=True
        )
    
    except ClientError as e:
        raise Exception(e.response["Error"]["Message"])


def start_pipeline(name: str) -> str:
    logger.info("Executing CI/CD pipeline with new model ...")
    cp_client = boto3.client("codepipeline")
    try:
        response = cp_client.start_pipeline_execution(
            name=name
        )
        execution_id = response["pipelineExecutionId"]
        logger.info(f"Pipeline Execution ID: {execution_id}")
        return execution_id
    
    except ClientError as e:
        raise Exception(e.response["Error"]["Message"])
