import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
import os

REGION = os.getenv("AWS_REGION", "us-east-1")
OS_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT") 

def get_bedrock_client():
    """Initializes the Bedrock Runtime client."""
    return boto3.client("bedrock-runtime", region_name=REGION)

def get_opensearch_client():
    """Initializes the OpenSearch client for vector operations."""
    return OpenSearch(
        hosts=[{'host': OS_ENDPOINT, 'port': 443}],
        http_auth=(os.getenv("OS_USER"), os.getenv("OS_PASS")),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
