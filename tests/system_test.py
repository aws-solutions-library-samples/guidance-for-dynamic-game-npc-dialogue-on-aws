""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import requests

def test_text_endpoint():
    # System test for the text api, before deploying into production
    with requests.post(
        os.environ["TEXT_ENDPOINT"],
        json={"question": "What are large language models?"},
        timeout=60
    ) as response:
        assert response.status_code == 200


def test_rag_endpoint():
    # System test for the text api (with RAG), before deploying into production
    # NOTE: This test does NOT test wether the OpenSearch INDEX is hydrated, but
    #       simply that the RAG API is functional.
    with requests.post(
        os.environ["RAG_ENDPOINT"],
        json={"question": "what is the address of the fiat customer center"},
        timeout=60
    ) as response:
        assert response.status_code == 200