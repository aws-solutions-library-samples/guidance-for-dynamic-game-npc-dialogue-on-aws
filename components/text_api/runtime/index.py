""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import json
import boto3

from typing import Dict
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Logger

# Environmental parameters
TEXT_MODEL_ID = os.environ["TEXT_MODEL_ID"]

# Global parameters
tracer = Tracer()
logger = Logger()
bedrock_client = boto3.client("bedrock-runtime")


@tracer.capture_lambda_handler
def lambda_handler(event, context): 
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    body = json.loads(event["body"])
    validate_response = validate_inputs(body)
    if validate_response:
        return validate_response
    question = body["question"]
    logger.info(f"Question: {question}")
    response = get_prediction(question=question)
    return build_response(
        {
            "response": response
        }
    )


def build_response(body: Dict) -> Dict:
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }


def validate_inputs(body: Dict):
    for input_name in ["question"]:
        if input_name not in body:
            return build_response(
                {
                    "status": "error",
                    "message": f"{input_name} missing in payload"
                }
            )


def get_prediction(question: str) -> str:
    prompt_template = f"""\n\nHuman: Your name is Ada, and you are a helpful assitant. Provide a concise answer to the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.
    
    Question: {question}
    
    \n\nAssistant:"""
    logger.info(f"Sending prompt to Bedrock (RAG disabled) ... ")
    response = bedrock_client.invoke_model(
        # Default model parameters for Claude v2
        body=json.dumps(
            {
                "prompt": prompt_template,
                "max_tokens_to_sample": 300,
                "temperature": 0.5,
                "top_k": 250,
                "top_p": 1,
                "stop_sequences": [
                    "\n\nHuman:"
                ],
                "anthropic_version": "bedrock-2023-05-31"
            }
        ),
        modelId=TEXT_MODEL_ID,
        accept="*/*",
        contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    answer = response_body.get("completion")
    logger.info(f"Bedrock returned the following answer: {answer}")
    return answer