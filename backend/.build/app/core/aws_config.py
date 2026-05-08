import boto3
import os
import logging
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger(__name__)

REGION = os.getenv("APP_AWS_REGION") or os.getenv("AWS_REGION") or "us-east-1"
# Matches the 'OPENSEARCH_URL' in your lambda.tf
OS_URL = os.getenv("OPENSEARCH_URL") 

def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=REGION)

def get_opensearch_client():
    if not OS_URL:
        # Prevent the 'None.replace' crash that causes the silent 500
        logger.error("CRITICAL: OPENSEARCH_URL environment variable is not set.")
        return None

    try:
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key, 
            credentials.secret_key, 
            REGION, 
            'es', 
            session_token=credentials.token
        )

        # Clean the URL (remove https:// and any trailing slashes)
        host = OS_URL.replace("https://", "").strip("/")

        return OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
    except Exception as e:
        logger.error(f"Failed to create OpenSearch client: {str(e)}")
        return None
    
