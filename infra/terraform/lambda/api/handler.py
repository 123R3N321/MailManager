import json
import os
import re
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

_s3 = boto3.client("s3")
_sqs = boto3.client("sqs")
_ddb = boto3.resource("dynamodb")


DEMO_USER_ID = "demo-user-001"


DEMO_DATA = {
    "mailboxes": [
        {
            "mailboxId": "mbx-gmail",
            "provider": "gmail",
            "email": "devansh.demo@gmail.com",
            "displayName": "Gmail Demo Inbox",
        },
        {
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "email": "devansh.work@outlook.com",
            "displayName": "Outlook Work Inbox",
        },
    ],
    "threads": [
        {
            "threadId": "thr-001",
            "mailboxId": "mbx-gmail",
            "provider": "gmail",
            "subject": "Q2 Pricing Approval Needed",
            "participants": ["alex@company.com", "devansh.demo@gmail.com"],
            "messages": [
                {
                    "messageId": "msg-001",
                    "from": "alex@company.com",
                    "to": ["devansh.demo@gmail.com"],
                    "sentAt": "2026-05-05T10:15:00Z",
                    "body": "Hi Devansh, can you review and approve the Q2 pricing sheet by Thursday? Finance needs it before the launch review.",
                },
                {
                    "messageId": "msg-002",
                    "from": "devansh.demo@gmail.com",
                    "to": ["alex@company.com"],
                    "sentAt": "2026-05-05T10:40:00Z",
                    "body": "Thanks Alex, I will review the pricing sheet and send approval before Thursday evening.",
                },
            ],
        },
        {
            "threadId": "thr-002",
            "mailboxId": "mbx-gmail",
            "provider": "gmail",
            "subject": "Acme Invoice Approval",
            "participants": ["finance@company.com", "devansh.demo@gmail.com"],
            "messages": [
                {
                    "messageId": "msg-003",
                    "from": "finance@company.com",
                    "to": ["devansh.demo@gmail.com"],
                    "sentAt": "2026-05-06T09:00:00Z",
                    "body": "Please approve the Acme vendor invoice by Friday. The payment is blocked until your approval is recorded.",
                }
            ],
        },
        {
            "threadId": "thr-003",
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "subject": "Client Onboarding Tasks",
            "participants": ["maya@client.com", "devansh.work@outlook.com"],
            "messages": [
                {
                    "messageId": "msg-004",
                    "from": "maya@client.com",
                    "to": ["devansh.work@outlook.com"],
                    "sentAt": "2026-05-04T14:20:00Z",
                    "body": "For onboarding, please send the AWS architecture diagram, API endpoint list, and security notes by Thursday morning.",
                },
                {
                    "messageId": "msg-005",
                    "from": "devansh.work@outlook.com",
                    "to": ["maya@client.com"],
                    "sentAt": "2026-05-04T15:10:00Z",
                    "body": "Got it. I will send the architecture diagram, endpoint list, and security notes before Thursday morning.",
                },
            ],
        },
        {
            "threadId": "thr-004",
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "subject": "Launch Review Meeting",
            "participants": ["pm@company.com", "devansh.work@outlook.com"],
            "messages": [
                {
                    "messageId": "msg-006",
                    "from": "pm@company.com",
                    "to": ["devansh.work@outlook.com"],
                    "sentAt": "2026-05-06T16:00:00Z",
                    "body": "The launch review is scheduled for Thursday at 5 PM. Please prepare a short demo script and confirm the search feature works.",
                }
            ],
        },
    ],
}


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body, default=_json_default),
    }


def _parse_body(event):
    raw = event.get("body") or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _get_table():
    return _ddb.Table(os.environ["TABLE_NAME"])


def _get_bucket():
    return os.environ["BUCKET_NAME"]


def _now():
    return int(time.time())


def _put_health(table, bucket_name, request_id):
    table.put_item(
        Item={
            "PK": "HEALTH",
            "SK": "CHECK",
            "updated_at": str(_now()),
            "request_id": request_id,
        }
    )

    _s3.put_object(
        Bucket=bucket_name,
        Key="_healthcheck/last.json",
        Body=json.dumps({"ts": _now(), "request_id": request_id}).encode("utf-8"),
        ContentType="application/json",
    )


def _ingest_demo(table, bucket_name):
    key = "demo/demo_emails.json"

    _s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(DEMO_DATA, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    for mailbox in DEMO_DATA["mailboxes"]:
        table.put_item(
            Item={
                "PK": f"USER#{DEMO_USER_ID}",
                "SK": f"MAILBOX#{mailbox['mailboxId']}",
                "entityType": "MailboxConnection",
                "userId": DEMO_USER_ID,
                **mailbox,
                "createdAt": str(_now()),
            }
        )

    message_count = 0

    for thread in DEMO_DATA["threads"]:
        messages = thread["messages"]
        preview = messages[-1]["body"][:160] if messages else ""

        table.put_item(
            Item={
                "PK": f"MAILBOX#{thread['mailboxId']}",
                "SK": f"THREAD#{thread['threadId']}",
                "entityType": "EmailThread",
                "userId": DEMO_USER_ID,
                "threadId": thread["threadId"],
                "mailboxId": thread["mailboxId"],
                "provider": thread["provider"],
                "subject": thread["subject"],
                "participants": thread["participants"],
                "messageCount": len(messages),
                "preview": preview,
                "rawS3Key": key,
                "createdAt": str(_now()),
            }
        )

        for msg in messages:
            message_count += 1
            table.put_item(
                Item={
                    "PK": f"THREAD#{thread['threadId']}",
                    "SK": f"MESSAGE#{msg['messageId']}",
                    "entityType": "EmailMessage",
                    "userId": DEMO_USER_ID,
                    "threadId": thread["threadId"],
                    "mailboxId": thread["mailboxId"],
                    "provider": thread["provider"],
                    "subject": thread["subject"],
                    **msg,
                }
            )

    return _response(
        200,
        {
            "status": "ingested",
            "mailboxes": len(DEMO_DATA["mailboxes"]),
            "threads": len(DEMO_DATA["threads"]),
            "messages": message_count,
            "s3Key": key,
        },
    )


def _list_mailboxes(table):
    result = table.scan(FilterExpression=Attr("entityType").eq("MailboxConnection"))
    mailboxes = [
        {
            "mailboxId": item["mailboxId"],
            "provider": item["provider"],
            "email": item["email"],
            "displayName": item["displayName"],
        }
        for item in result.get("Items", [])
    ]
    return _response(200, {"userId": DEMO_USER_ID, "mailboxes": mailboxes})


def _list_threads(table, mailbox_id=None):
    items = []

    scan = table.scan(FilterExpression=Attr("entityType").eq("EmailThread"))
    for item in scan.get("Items", []):
        if mailbox_id and item.get("mailboxId") != mailbox_id:
            continue
        items.append(
            {
                "threadId": item["threadId"],
                "mailboxId": item["mailboxId"],
                "provider": item["provider"],
                "subject": item["subject"],
                "participants": item.get("participants", []),
                "messageCount": item.get("messageCount", 0),
                "preview": item.get("preview", ""),
            }
        )

    return _response(200, {"threads": items})


def _get_thread(table, thread_id):
    thread_scan = table.scan(
        FilterExpression=Attr("entityType").eq("EmailThread") & Attr("threadId").eq(thread_id)
    )
    threads = thread_scan.get("Items", [])

    if not threads:
        return _response(404, {"error": "thread_not_found", "threadId": thread_id})

    msg_scan = table.scan(
        FilterExpression=Attr("entityType").eq("EmailMessage") & Attr("threadId").eq(thread_id)
    )
    messages = sorted(msg_scan.get("Items", []), key=lambda m: m.get("sentAt", ""))

    thread = threads[0]
    return _response(
        200,
        {
            "thread": {
                "threadId": thread["threadId"],
                "mailboxId": thread["mailboxId"],
                "provider": thread["provider"],
                "subject": thread["subject"],
                "participants": thread.get("participants", []),
                "messages": messages,
            }
        },
    )


def _all_messages(table, mailbox_id=None):
    result = table.scan(FilterExpression=Attr("entityType").eq("EmailMessage"))
    messages = []
    for item in result.get("Items", []):
        if mailbox_id and item.get("mailboxId") != mailbox_id:
            continue
        messages.append(item)
    return messages


def _search(table, event):
    body = _parse_body(event)
    query = body.get("query", "").strip()
    mailbox_id = body.get("mailboxId")

    if not query:
        return _response(400, {"error": "missing_query"})

    terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]+", query) if len(t) > 2]
    messages = _all_messages(table, mailbox_id)

    scored = []
    for msg in messages:
        text = f"{msg.get('subject', '')} {msg.get('body', '')}".lower()
        score = sum(text.count(term) for term in terms)

        if score > 0:
            scored.append((score, msg))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]

    sources = [
        {
            "threadId": msg["threadId"],
            "messageId": msg["messageId"],
            "mailboxId": msg["mailboxId"],
            "provider": msg["provider"],
            "subject": msg["subject"],
            "sender": msg["from"],
            "sentAt": msg["sentAt"],
            "snippet": msg["body"][:220],
            "score": score,
        }
        for score, msg in top
    ]

    if not sources:
        answer = "I could not find enough evidence in the selected mailbox to answer that."
    else:
        joined = " ".join(src["snippet"] for src in sources[:2])
        answer = f"Based on the matching emails, the main relevant information is: {joined}"

    return _response(
        200,
        {
            "query": query,
            "answer": answer,
            "sources": sources,
            "retrievalMode": "keyword-fallback",
            "model": "template",
        },
    )


def _summary(table, thread_id):
    thread_resp = json.loads(_get_thread(table, thread_id)["body"])
    if "error" in thread_resp:
        return _response(404, thread_resp)

    thread = thread_resp["thread"]
    messages = thread["messages"]
    bullets = [m["body"][:180] for m in messages[:3]]

    return _response(
        200,
        {
            "threadId": thread_id,
            "summary": {
                "short": f"This thread is about: {thread['subject']}.",
                "keyPoints": bullets,
                "openQuestions": ["Confirm completion status and next deadline if needed."],
            },
            "model": "template",
        },
    )


def _draft_reply(table, thread_id, event):
    body = _parse_body(event)
    intent = body.get("intent", "acknowledge and confirm next steps")

    thread_resp = json.loads(_get_thread(table, thread_id)["body"])
    if "error" in thread_resp:
        return _response(404, thread_resp)

    subject = thread_resp["thread"]["subject"]

    draft = (
        f"Hi,\n\nThanks for the update on {subject}. "
        f"I will {intent}. Please let me know if there is anything else I should include.\n\n"
        "Best,\nDevansh"
    )

    return _response(
        200,
        {
            "threadId": thread_id,
            "draft": draft,
            "model": "template",
        },
    )


def _action_items(table, thread_id):
    thread_resp = json.loads(_get_thread(table, thread_id)["body"])
    if "error" in thread_resp:
        return _response(404, thread_resp)

    action_items = []
    messages = thread_resp["thread"]["messages"]

    keywords = ["please", "need", "approve", "send", "prepare", "confirm", "review"]
    for msg in messages:
        body = msg.get("body", "")
        lower = body.lower()
        if any(k in lower for k in keywords):
            action_items.append(
                {
                    "task": body[:160],
                    "owner": "Devansh",
                    "dueDate": "Check email context",
                    "priority": "medium",
                    "sourceMessageId": msg["messageId"],
                    "status": "open",
                }
            )

    return _response(
        200,
        {
            "threadId": thread_id,
            "actionItems": action_items,
            "model": "template",
        },
    )


def handler(event, context):
    table = _get_table()
    bucket_name = _get_bucket()
    queue_url = os.environ.get("QUEUE_URL", "")

    method = (event.get("requestContext") or {}).get("http", {}).get("method", "")
    path = (event.get("requestContext") or {}).get("http", {}).get("path", "")
    query = event.get("queryStringParameters") or {}

    if method == "OPTIONS":
        return _response(200, {"status": "ok"})

    if method == "GET" and path == "/health":
        _put_health(table, bucket_name, context.aws_request_id)
        return _response(
            200,
            {
                "status": "ok",
                "service": "mailmanager-api",
                "table": os.environ["TABLE_NAME"],
                "bucket": bucket_name,
                "queue_configured": bool(queue_url),
            },
        )

    if method == "POST" and path == "/enqueue":
        if not queue_url:
            return _response(501, {"error": "queue_not_configured"})
        body_text = (event.get("body") or "").strip() or '{"source":"manual"}'
        _sqs.send_message(QueueUrl=queue_url, MessageBody=body_text)
        return _response(202, {"status": "enqueued", "preview": body_text[:500]})

    if method == "POST" and path == "/ingest/demo":
        return _ingest_demo(table, bucket_name)

    if method == "GET" and path == "/mailboxes":
        return _list_mailboxes(table)

    if method == "GET" and path == "/threads":
        return _list_threads(table, query.get("mailboxId"))

    if method == "GET" and path.startswith("/threads/"):
        thread_id = path.split("/")[-1]
        return _get_thread(table, thread_id)

    if method == "POST" and path == "/search":
        return _search(table, event)

    if method == "POST" and path.startswith("/threads/") and path.endswith("/summary"):
        thread_id = path.split("/")[2]
        return _summary(table, thread_id)

    if method == "POST" and path.startswith("/threads/") and path.endswith("/draft-reply"):
        thread_id = path.split("/")[2]
        return _draft_reply(table, thread_id, event)

    if method == "POST" and path.startswith("/threads/") and path.endswith("/action-items"):
        thread_id = path.split("/")[2]
        return _action_items(table, thread_id)

    return _response(404, {"error": "not_found", "method": method, "path": path})