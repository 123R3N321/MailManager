import json
import logging
import os
import urllib.error
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_s3 = boto3.client("s3")
_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("BEDROCK_REGION", "us-east-1"),
)

OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "").rstrip("/")
INDEX_NAME = os.environ.get("INDEX_NAME", "mailmanager-index")
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")
REGION = os.environ.get("APP_AWS_REGION", "us-east-1")


def _get_embedding(text):
    response = _bedrock.invoke_model(
        body=json.dumps({"inputText": text}),
        modelId=EMBEDDING_MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )
    return json.loads(response["body"].read())["embedding"]


def _index_document(doc_id, payload):
    if not OPENSEARCH_URL:
        raise ValueError("OPENSEARCH_URL is not configured")

    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_doc/{doc_id}"
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    aws_request = AWSRequest(method="PUT", url=url, data=body, headers=headers)
    credentials = boto3.Session().get_credentials()
    SigV4Auth(credentials.get_frozen_credentials(), "es", REGION).add_auth(aws_request)

    prepared = aws_request.prepare()
    http_request = urllib.request.Request(
        url=prepared.url,
        data=body,
        headers=dict(prepared.headers),
        method="PUT",
    )

    try:
        with urllib.request.urlopen(http_request, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("OpenSearch HTTP %s indexing %s: %s", exc.code, doc_id, error_body)
        return None


def handler(event, context):
    records = event.get("Records", [])
    total_indexed = 0

    for record in records:
        try:
            sqs_body = json.loads(record["body"])
            bucket = sqs_body["bucket"]
            key = sqs_body["key"]

            logger.info("Processing s3://%s/%s", bucket, key)

            obj = _s3.get_object(Bucket=bucket, Key=key)
            raw = json.loads(obj["Body"].read())

            threads = raw.get("threads", [])
            logger.info("Found %d threads", len(threads))

            for thread in threads:
                thread_id = thread.get("threadId")
                subject = thread.get("subject", "No Subject")
                mailbox_id = thread.get("mailboxId")

                for msg in thread.get("messages", []):
                    body_text = msg.get("body", "")
                    text_to_embed = f"Subject: {subject} From: {msg.get('from', '')} Body: {body_text}"

                    vector = _get_embedding(text_to_embed)

                    doc = {
                        "messageId": msg.get("messageId"),
                        "threadId": thread_id,
                        "mailboxId": mailbox_id,
                        "subject": subject,
                        "sender": msg.get("from"),
                        "sentAt": msg.get("sentAt"),
                        "snippet": body_text[:200],
                        "body": body_text,
                        "email_vector": vector,
                    }

                    status = _index_document(msg.get("messageId", "unknown"), doc)
                    if status in (200, 201):
                        total_indexed += 1

            logger.info("Indexed %d messages total", total_indexed)

        except Exception as exc:
            logger.exception("Worker error processing record: %s", exc)
            continue

    return {"statusCode": 200, "body": json.dumps({"total_indexed": total_indexed})}
