""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import json
import boto3
import base64

from typing import Dict
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Logger

# Environmental parameters
TEXT_MODEL_ID = os.environ["TEXT_MODEL_ID"]

# Global parameters
tracer = Tracer()
logger = Logger()
bedrock_client = boto3.client("bedrock-runtime")
polly_client = boto3.client("polly")

@tracer.capture_lambda_handler
def lambda_handler(event, context): 
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    body = json.loads(event["body"])
    validate_response = validate_inputs(body)
    if validate_response:
        return validate_response
    question = body["question"]
    # if the voice_id or voice_engine isn't specified, use default values
    voice_id = body.get("voice_id", "Ruth")
    voice_engine = body.get("voice_engine", "neural")
    logger.info(f"Question: {question}")
    logger.info(f"Voice ID: {voice_id}")
    logger.info(f"Voice Engine: {voice_engine}")

    response = get_prediction(question=question)

    speech_info = synthesize_speech(text = response, 
        voice_id = voice_id,
        voice_engine = voice_engine)

    return build_response(
        {
            "response": response,
            "speech_info" : speech_info
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

def synthesize_speech(text: str, voice_id: str, voice_engine: str):
    # given text to synthesize along with the voice ID and engine, this will 
    # get a buffer with the pcm in 1 channel 16-bit at 16k and then will
    # get a buffer with json that has all of the viseme timings
    speech_info = {}
    
    try:
        sound_response = polly_client.synthesize_speech(
            OutputFormat = "pcm",
            Text = text,
            VoiceId = voice_id,
            Engine = voice_engine
        )
        audio_stream = sound_response["AudioStream"]
        speech_info['sound_status'] = "ok"
        speech_info['sound_response'] = base64.b64encode(audio_stream.read()).decode("utf-8")
    except Exception as e:
        speech_info['sound_status'] = "error"
        exception_str = f"Audio Exception: {type(e).__name__} Message: {str(e)}"
        speech_info['sound_error'] = exception_str
        logger.info(exception_str)
    
    try:
        viseme_response = polly_client.synthesize_speech(
            OutputFormat = "json",
            SpeechMarkTypes = ["viseme"],
            Text = text,
            VoiceId = voice_id,
            Engine = voice_engine
        )
        viseme_strem = viseme_response["AudioStream"]
        speech_info['viseme_status'] = "ok"
        speech_info['viseme_response'] = base64.b64encode(viseme_strem.read()).decode("utf-8")
    except Exception as e:
        speech_info['viseme_status'] = "error"
        exception_str = f"Viseme Exception: {type(e).__name__} Message: {str(e)}"
        speech_info['viseme_error'] = exception_str
        logger.info(exception_str)
    
    return speech_info
    
def get_prediction(question: str) -> str:
    logger.info(f"Sending prompt to Bedrock (RAG disabled) ... ")
    response = bedrock_client.invoke_model(
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Your name is Ada, and you are a helpful assistant. Provide a concise answer to the question. If you don't know the answer, just say that you don't know, don't try to make up an answer.\n\nQuestion: {question}"
                    }
                ],
                "temperature": 0.5,
                "top_k": 250
            }
        ),
        modelId=TEXT_MODEL_ID,
        accept="application/json",
        contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    answer = response_body["content"][0]["text"]
    logger.info(f"Bedrock returned the following answer: {answer}")
    return answer