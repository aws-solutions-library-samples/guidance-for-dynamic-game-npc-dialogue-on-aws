""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import boto3
import json

from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Logger

# Global parameters
tracer = Tracer()
logger = Logger()
sm_client = boto3.client("sagemaker")


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    logger.info("Starting SageMaker Pipeline Execution ...")
    try:
        response = sm_client.start_pipeline_execution(
            PipelineName=os.environ["PIPELINE_NAME"],
            PipelineParameters=[
                {"Name": "BaseModel", "Value": os.environ["BASE_MODEL"]},
                {"Name": "DataBucket", "Value": event["Records"][0]["s3"]["bucket"]["name"]},
                {"Name": "DataPrefix", "Value": event["Records"][0]["s3"]["object"]["key"]},
                {"Name": "Epochs", "Value": str(os.environ["EPOCHS"])},
                {"Name": "BatchSize", "Value": str(os.environ["BATCHES"])},
                {"Name": "LearningRate", "Value": str(os.environ["LEARNING_RATE"])},
                {"Name": "WarmupSteps", "Value": str(os.environ["WARMUP_STEPS"])}
            ]
        )
        execution_arn = response["PipelineExecutionArn"]
        logger.info(f"SageMaker Pipeline Execution ARN: {execution_arn}")
        return {
            "statusCode": 200,
            "body": execution_arn
        }
    
    except ClientError as e:
        message = e.response["Error"]["Message"]
        raise Exception(message)
