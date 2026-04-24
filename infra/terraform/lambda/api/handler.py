import json
import os
import time

import boto3

_s3 = boto3.client("s3")
_ddb = boto3.resource("dynamodb")


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    table_name = os.environ["TABLE_NAME"]
    bucket_name = os.environ["BUCKET_NAME"]
    queue_url = os.environ.get("QUEUE_URL", "")

    table = _ddb.Table(table_name)
    table.put_item(
        Item={
            "PK": "HEALTH",
            "SK": "CHECK",
            "updated_at": str(int(time.time())),
            "request_id": context.aws_request_id,
        }
    )

    key = "_healthcheck/last.json"
    _s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps({"ts": int(time.time()), "request_id": context.aws_request_id}).encode("utf-8"),
        ContentType="application/json",
    )

    body = {
        "status": "ok",
        "service": "mailmanager-api",
        "table": table_name,
        "bucket": bucket_name,
        "queue_configured": bool(queue_url),
    }

    route = (event.get("requestContext") or {}).get("http", {}).get("method")
    path = (event.get("requestContext") or {}).get("http", {}).get("path")
    if route == "POST" and path == "/enqueue":
        if not queue_url:
            return _response(501, {"error": "queue_not_configured"})
        body_text = (event.get("body") or "").strip() or '{"source":"manual"}'
        boto3.client("sqs").send_message(QueueUrl=queue_url, MessageBody=body_text)
        return _response(202, {"status": "enqueued", "preview": body_text[:500]})

    return _response(200, body)
