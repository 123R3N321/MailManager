import json
import os
import boto3
import logging
import requests
from requests_aws4auth import AWS4Auth

# --- CRITICAL: Initialize Logger ---
# This ensures logger is defined globally and available to all functions
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS Clients
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('BEDROCK_REGION', 'us-east-1'))

# Environment Variables from Terraform
OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL')
INDEX_NAME = os.environ.get('INDEX_NAME')
EMBEDDING_MODEL_ID = os.environ.get('EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v1')
REGION = os.environ.get('APP_AWS_REGION', 'us-east-1')

def get_embedding(text):
    """Generates vector embedding via Amazon Bedrock Titan."""
    body = json.dumps({"inputText": text})
    try:
        response = bedrock.invoke_model(
            body=body,
            modelId=EMBEDDING_MODEL_ID,
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        return response_body.get('embedding')
    except Exception as e:
        logger.error(f"Bedrock Embedding Error: {str(e)}")
        raise

def index_in_opensearch(email_data, vector):
    """Indexes the document and its vector into OpenSearch."""
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key, 
        credentials.secret_key, 
        REGION, 
        service, 
        session_token=credentials.token
    )

    doc_id = email_data.get('messageId', 'unknown')
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_doc/{doc_id}"
    
    payload = {
        **email_data,
        "email_vector": vector 
    }
    
    try:
        r = requests.put(url, auth=awsauth, json=payload, headers={"Content-Type": "application/json"})
        r.raise_for_status()
        return r.status_code
    except Exception as e:
        logger.error(f"OpenSearch Indexing Error: {str(e)}")
        return None

def handler(event, context):
    records = event.get('Records', [])
    total_indexed = 0

    for record in records:
        try:
            sqs_body = json.loads(record['body'])
            bucket = sqs_body['bucket']
            key = sqs_body['key']
            
            logger.info(f"Processing S3 file: s3://{bucket}/{key}")
            
            obj = s3.get_object(Bucket=bucket, Key=key)
            raw_content = json.loads(obj['Body'].read())

            # --- TARGETED THREAD PARSING ---
            # Drilling down: threads[] -> messages[]
            threads = raw_content.get('threads', [])
            logger.info(f"Detected {len(threads)} threads.")
            
            for thread in threads:
                thread_id = thread.get('threadId')
                subject = thread.get('subject', 'No Subject')
                mailbox_id = thread.get('mailboxId')
                messages = thread.get('messages', [])
                
                for msg in messages:
                    # Construct rich text for embedding
                    body_content = msg.get('body', '')
                    text_to_embed = f"Subject: {subject} From: {msg.get('from')} Body: {body_content}"
                    
                    # 1. Generate Vector
                    vector = get_embedding(text_to_embed)
                    
                    # 2. Build the final document
                    email_doc = {
                        "messageId": msg.get('messageId'),
                        "threadId": thread_id,
                        "mailboxId": mailbox_id,
                        "subject": subject,
                        "sender": msg.get('from'),
                        "sentAt": msg.get('sentAt'),
                        "snippet": body_content[:200], 
                        "body": body_content
                    }
                    
                    # 3. Index in OpenSearch
                    status = index_in_opensearch(email_doc, vector)
                    if status in [200, 201]:
                        total_indexed += 1

            logger.info(f"Success: Indexed {total_indexed} total messages.")

        except Exception as e:
            # Now logger is guaranteed to be defined
            logger.error(f"Critical Worker Error: {str(e)}")
            continue

    return {
        "statusCode": 200,
        "body": json.dumps({"total_indexed": total_indexed})
    }
