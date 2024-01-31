""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import json
import boto3
import logging
import argparse
import requests
import time

from requests.auth import HTTPBasicAuth
from typing import List, Any
from tqdm import tqdm
from langchain.text_splitter import RecursiveCharacterTextSplitter
from botocore.exceptions import ClientError

# Script parameters
BASE_DIR = "/opt/ml/processing"
INPUT_PATH = os.path.join(BASE_DIR, "input", "data")
OUTPUT_PATH = os.path.join(BASE_DIR, "output")

def get_embedding(passage: str, model_id: str) -> List[float]:
    body = json.dumps(
        {
            "inputText": f"{passage}"
        }
    )
    try:
        request = bedrock_client.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        response = json.loads(request.get("body").read())
        embedding = response.get("embedding")
        return embedding
    
    except ClientError as e:
        message = e.response["Error"]["Message"]
        logger.error(message)
        raise e


def get_credentials(secret_id: str, region: str) -> str:
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_id)
        json_body = json.loads(response["SecretString"])
        return json_body["USERNAME"], json_body["PASSWORD"]
    
    except ClientError as e:
        message = e.response["Error"]["Message"]
        logger.error(message)
        raise e


def verify_index(endpoint: str, index: str, username: str, password: str) -> Any:
    url = f"{endpoint}/{index}"
    knn_index = {
        "settings": {
            "index": {
                "knn": True  # Enable k-NN search for this index
            }
        },
        "mappings": {
            "properties": {
                "vector_field": {  # k-NN vector field
                    "type": "knn_vector",
                    "dimension": 1536,  # Dimension of the vector
                    "similarity": "cosine"
                },
                "file_name": {
                    "type": "text"
                },
                "page": {
                    "type": "text"
                },
                "passage": {
                    "type": "text"
                }
            }
        }
    }
    response = requests.head(url, auth=HTTPBasicAuth(username, password), timeout=10)
    if response.status_code != 404:
        logger.info(f"{index} already exists!")
        response = requests.delete(url, auth=HTTPBasicAuth(username, password), timeout=10)
    logger.info(f"Creating fresh index: {index}")
    response = requests.put(url, auth=HTTPBasicAuth(username, password), json=knn_index, timeout=10)
    logger.info(f"Fresh index created: {response.text}")


def doc_iterator(dir_path: str) -> str:
    for root, _, filenames in os.walk(dir_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            page = filename.split(".")[0].split("_")[-1]
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_contents = f.read()
                    yield filename, page, file_contents


def create_chunks(data_path: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    chunks = []
    total_passages = 0
    try:
        for file_name, page, doc in tqdm(doc_iterator(data_path)):
            n_passages = 0
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
                chunk_overlap=chunk_overlap,
            )
            tmp_chunks = text_splitter.split_text(doc)
            for i, chunk in enumerate(tmp_chunks):
                chunks.append({
                    "file_name": file_name,
                    "page": page,
                    "passage": chunk
                })
                n_passages += 1
                total_passages += 1
            logger.info(f"Document segmented into {n_passages} passages")
        logger.info(f"Total passages to index: {total_passages}")
        return chunks
    
    except Exception as e:
        raise e


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler(f"{OUTPUT_PATH}/job.log"),
            logging.StreamHandler()
        ]
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-model", type=str, default="amazon.titan-tg1-large")
    parser.add_argument("--embedding-model", type=str, default="amazon.titan-e1t-medium")
    parser.add_argument("--opensearch-domain", type=str, default=None)
    parser.add_argument("--opensearch-secret", type=str, default=None)
    parser.add_argument("--opensearch-index", type=str, default=None)
    parser.add_argument("--region", type=str, default=None)
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--overlap", type=int, default=0)
    args = parser.parse_args()
    logger.info(f"Arguments: {args}")

    # Create the Bedrock runtime client
    bedrock_client = boto3.client("bedrock-runtime", region_name=args.region)
    logger.info("Starting OpenSearch data ingestion ...")
    start_time = time.time()

    # Convert all documents into chunks using LangChain
    logger.info("Splitting documents into chunks ...")
    chunks = create_chunks(data_path=INPUT_PATH, chunk_size=args.chunk_size, chunk_overlap=args.overlap)

    # Store each chunk, including the vector representation, in OpenSearch
    i = 1
    username, password = get_credentials(args.opensearch_secret, args.region)
    domain_endpoint = f"https://{args.opensearch_domain}" if not args.opensearch_domain.startswith("https://") else args.opensearch_domain
    domain_index = args.opensearch_index
    verify_index(endpoint=domain_endpoint, index=domain_index, username=username, password=password)
    logger.info("Ingesting chunks into OpenSearch ...")
    for chunk in chunks:
        passage = chunk["passage"]
        document = {
            "vector_field": get_embedding(passage=passage, model_id=args.embedding_model),
            "file_name": chunk["file_name"],
            "page": chunk["page"],
            "passage": passage
        }
        response = requests.post(f"{domain_endpoint}/{domain_index}/_doc/{i}", auth=HTTPBasicAuth(username, password), json=document, timeout=10)
        i += 1
        if response.status_code not in [200, 201]:
            logger.info(f"Chunk ingest failure: {response.status_code}, Message: {response.text}")
        else:
            logger.info(response.text)
    logger.info(f"OpenSearch data ingestion complete. Duration: {time.strftime('%H:%M:%S', time.gmtime(time.time() - start_time))}")
