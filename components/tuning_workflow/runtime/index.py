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
sfn_client = boto3.client("stepfunctions")


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    for record in event["Records"]:
        payload = json.loads(record["body"])
        if payload.get("status") != "Stopping":
            logger.info("Starting State Machine Execution ...")
            try:
                response = sfn_client.start_execution(
                    stateMachineArn=os.environ["STATE_MACHINE_ARN"],
                    input=json.dumps(
                        {
                            "status": "Start",
                            "parameters": payload.get("arguments"),
                            "token": payload.get("token")
                        }
                    )
                )
                execution_arn = response["executionArn"]
                logger.info(f"Execution ARN: {execution_arn}")
                return {
                    "statusCode": 200,
                    "body": execution_arn
                }
            
            except ClientError as e:
                message = e.response["Error"]["Message"]
                raise Exception(message)
        else:
            try:
                sm_client.send_pipeline_execution_step_failure(
                    CallbackToken=payload.get("token"),
                    FailureReason="Manual Stopping Behavior"
                )
            
            except ClientError as e:
                message = e.response["Error"]["Message"]
                raise Exception(message)
