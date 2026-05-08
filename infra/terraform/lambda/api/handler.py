import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from decimal import Decimal

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from boto3.dynamodb.conditions import Attr

_s3 = boto3.client("s3")
_sqs = boto3.client("sqs")
_ddb = boto3.resource("dynamodb")
_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("BEDROCK_REGION") or os.environ.get("APP_AWS_REGION", "us-east-1"),
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEMO_USER_ID = "demo-user-001"
DEFAULT_BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v1"


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
            "subject": "Acme Invoice Approval - Due Friday",
            "participants": ["finance@company.com", "alex@company.com", "devansh.demo@gmail.com"],
            "messages": [
                {
                    "messageId": "msg-001",
                    "from": "finance@company.com",
                    "to": ["devansh.demo@gmail.com"],
                    "sentAt": "2026-05-04T09:15:00Z",
                    "body": "Hi Devansh, Acme submitted invoice INV-2048 for $18,420. Please review the attached services breakdown and approve payment by Friday morning so Accounts Payable can release funds.",
                },
                {
                    "messageId": "msg-002",
                    "from": "devansh.demo@gmail.com",
                    "to": ["finance@company.com"],
                    "sentAt": "2026-05-04T10:02:00Z",
                    "body": "Thanks. I am checking the April implementation hours against the statement of work and will confirm whether the invoice is approved by Thursday evening.",
                },
                {
                    "messageId": "msg-003",
                    "from": "alex@company.com",
                    "to": ["devansh.demo@gmail.com", "finance@company.com"],
                    "sentAt": "2026-05-05T13:35:00Z",
                    "body": "The Acme hours match the signed work order. Devansh, please send final approval by Friday at noon. Finance will mark this as blocked until your reply.",
                },
                {
                    "messageId": "msg-004",
                    "from": "devansh.demo@gmail.com",
                    "to": ["finance@company.com", "alex@company.com"],
                    "sentAt": "2026-05-05T15:10:00Z",
                    "body": "Confirmed. I approved invoice INV-2048 and Finance can proceed with payment on Friday morning.",
                },
            ],
        },
        {
            "threadId": "thr-002",
            "mailboxId": "mbx-gmail",
            "provider": "gmail",
            "subject": "Q2 Pricing Approval Before Launch",
            "participants": ["alex@company.com", "nina@company.com", "devansh.demo@gmail.com"],
            "messages": [
                {
                    "messageId": "msg-005",
                    "from": "alex@company.com",
                    "to": ["devansh.demo@gmail.com"],
                    "sentAt": "2026-05-04T11:30:00Z",
                    "body": "Can you review and approve the Q2 pricing sheet by Thursday? Sales needs the approved numbers before the launch review.",
                },
                {
                    "messageId": "msg-006",
                    "from": "nina@company.com",
                    "to": ["alex@company.com", "devansh.demo@gmail.com"],
                    "sentAt": "2026-05-04T13:10:00Z",
                    "body": "The only open item is the enterprise tier discount. If Devansh approves the 12 percent cap by Thursday afternoon, I can update the sales deck by evening.",
                },
                {
                    "messageId": "msg-007",
                    "from": "devansh.demo@gmail.com",
                    "to": ["alex@company.com", "nina@company.com"],
                    "sentAt": "2026-05-05T09:00:00Z",
                    "body": "I reviewed the Q2 pricing sheet. I approve the 12 percent enterprise discount cap, and I will send a final note before Thursday afternoon.",
                },
            ],
        },
        {
            "threadId": "thr-003",
            "mailboxId": "mbx-gmail",
            "provider": "gmail",
            "subject": "Launch Deadline Checklist",
            "participants": ["pm@company.com", "qa@company.com", "devansh.demo@gmail.com"],
            "messages": [
                {
                    "messageId": "msg-008",
                    "from": "pm@company.com",
                    "to": ["devansh.demo@gmail.com", "qa@company.com"],
                    "sentAt": "2026-05-05T08:20:00Z",
                    "body": "The launch review is Thursday at 5 PM. Please prepare the demo script, verify search works against both mailboxes, and send final launch notes by Thursday morning.",
                },
                {
                    "messageId": "msg-009",
                    "from": "qa@company.com",
                    "to": ["pm@company.com", "devansh.demo@gmail.com"],
                    "sentAt": "2026-05-05T14:25:00Z",
                    "body": "QA passed thread detail and mailbox switching. Search still needs one more check tomorrow morning after the demo data refresh.",
                },
                {
                    "messageId": "msg-010",
                    "from": "devansh.demo@gmail.com",
                    "to": ["pm@company.com", "qa@company.com"],
                    "sentAt": "2026-05-05T16:45:00Z",
                    "body": "I will refresh demo data tomorrow morning, confirm search, and send the launch notes before Thursday noon.",
                },
                {
                    "messageId": "msg-011",
                    "from": "pm@company.com",
                    "to": ["devansh.demo@gmail.com"],
                    "sentAt": "2026-05-06T09:40:00Z",
                    "body": "Thanks. Please also include the API base URL and known limitations in the launch notes by Thursday evening.",
                },
            ],
        },
        {
            "threadId": "thr-004",
            "mailboxId": "mbx-gmail",
            "provider": "gmail",
            "subject": "Vendor Contract Review",
            "participants": ["legal@company.com", "procurement@company.com", "devansh.demo@gmail.com"],
            "messages": [
                {
                    "messageId": "msg-012",
                    "from": "legal@company.com",
                    "to": ["devansh.demo@gmail.com", "procurement@company.com"],
                    "sentAt": "2026-05-03T15:05:00Z",
                    "body": "Please review the Northstar vendor contract and confirm whether the data retention clause is acceptable by Friday afternoon.",
                },
                {
                    "messageId": "msg-013",
                    "from": "procurement@company.com",
                    "to": ["legal@company.com", "devansh.demo@gmail.com"],
                    "sentAt": "2026-05-04T08:45:00Z",
                    "body": "Commercial terms are approved. Devansh only needs to confirm the security appendix and data retention language before we route for signature.",
                },
                {
                    "messageId": "msg-014",
                    "from": "devansh.demo@gmail.com",
                    "to": ["legal@company.com", "procurement@company.com"],
                    "sentAt": "2026-05-04T12:30:00Z",
                    "body": "I will review the security appendix today and send comments by Friday morning. The retention clause likely needs a 30-day deletion commitment.",
                },
            ],
        },
        {
            "threadId": "thr-005",
            "mailboxId": "mbx-gmail",
            "provider": "gmail",
            "subject": "Customer Meeting Scheduling",
            "participants": ["maya@client.com", "sales@company.com", "devansh.demo@gmail.com"],
            "messages": [
                {
                    "messageId": "msg-015",
                    "from": "maya@client.com",
                    "to": ["devansh.demo@gmail.com", "sales@company.com"],
                    "sentAt": "2026-05-05T12:00:00Z",
                    "body": "Could we schedule the onboarding kickoff for Thursday morning or Friday afternoon? We need the AWS setup owner and security reviewer included.",
                },
                {
                    "messageId": "msg-016",
                    "from": "sales@company.com",
                    "to": ["maya@client.com", "devansh.demo@gmail.com"],
                    "sentAt": "2026-05-05T12:25:00Z",
                    "body": "Friday afternoon works for Sales. Devansh, please confirm your availability and send a calendar hold by tomorrow.",
                },
                {
                    "messageId": "msg-017",
                    "from": "devansh.demo@gmail.com",
                    "to": ["maya@client.com", "sales@company.com"],
                    "sentAt": "2026-05-05T13:00:00Z",
                    "body": "Friday afternoon works for me. I will send a calendar invite tomorrow morning with the AWS setup owner and security reviewer copied.",
                },
            ],
        },
        {
            "threadId": "thr-006",
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "subject": "AWS Setup for Client Sandbox",
            "participants": ["cloudops@company.com", "maya@client.com", "devansh.work@outlook.com"],
            "messages": [
                {
                    "messageId": "msg-018",
                    "from": "cloudops@company.com",
                    "to": ["devansh.work@outlook.com"],
                    "sentAt": "2026-05-04T10:15:00Z",
                    "body": "The client sandbox AWS account is ready. Please confirm the API Gateway URL, Lambda environment variables, and DynamoDB table name by Thursday morning.",
                },
                {
                    "messageId": "msg-019",
                    "from": "devansh.work@outlook.com",
                    "to": ["cloudops@company.com"],
                    "sentAt": "2026-05-04T11:05:00Z",
                    "body": "I confirmed the Lambda environment variables. I still need to verify the API Gateway URL and DynamoDB table name before Thursday.",
                },
                {
                    "messageId": "msg-020",
                    "from": "maya@client.com",
                    "to": ["devansh.work@outlook.com", "cloudops@company.com"],
                    "sentAt": "2026-05-05T09:30:00Z",
                    "body": "Please send the final endpoint list by Thursday evening so our onboarding team can whitelist the URLs.",
                },
                {
                    "messageId": "msg-021",
                    "from": "devansh.work@outlook.com",
                    "to": ["maya@client.com", "cloudops@company.com"],
                    "sentAt": "2026-05-05T16:05:00Z",
                    "body": "I will send the final endpoint list by Thursday evening after validating the deployed API base URL.",
                },
            ],
        },
        {
            "threadId": "thr-007",
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "subject": "Security Review Findings",
            "participants": ["security@company.com", "cloudops@company.com", "devansh.work@outlook.com"],
            "messages": [
                {
                    "messageId": "msg-022",
                    "from": "security@company.com",
                    "to": ["devansh.work@outlook.com"],
                    "sentAt": "2026-05-04T14:00:00Z",
                    "body": "Security review is mostly clear. Please confirm CORS is restricted for production, secrets are not stored in code, and demo data contains no customer PII by Friday morning.",
                },
                {
                    "messageId": "msg-023",
                    "from": "devansh.work@outlook.com",
                    "to": ["security@company.com"],
                    "sentAt": "2026-05-04T15:20:00Z",
                    "body": "Confirmed no secrets are stored in code. I will document CORS status and demo data scope by Friday morning.",
                },
                {
                    "messageId": "msg-024",
                    "from": "cloudops@company.com",
                    "to": ["security@company.com", "devansh.work@outlook.com"],
                    "sentAt": "2026-05-05T10:10:00Z",
                    "body": "CloudOps verified IAM policies are least privilege for the demo. Devansh, please attach the notes to the security review thread before Friday afternoon.",
                },
            ],
        },
        {
            "threadId": "thr-008",
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "subject": "New Customer Onboarding Packet",
            "participants": ["onboarding@company.com", "maya@client.com", "devansh.work@outlook.com"],
            "messages": [
                {
                    "messageId": "msg-025",
                    "from": "onboarding@company.com",
                    "to": ["devansh.work@outlook.com", "maya@client.com"],
                    "sentAt": "2026-05-03T13:15:00Z",
                    "body": "For onboarding, please send the architecture diagram, API endpoint list, support contact, and security notes by Thursday morning.",
                },
                {
                    "messageId": "msg-026",
                    "from": "maya@client.com",
                    "to": ["onboarding@company.com", "devansh.work@outlook.com"],
                    "sentAt": "2026-05-03T14:00:00Z",
                    "body": "Please include a short explanation of how mailbox search sources are shown in the UI. Our team needs it before the kickoff.",
                },
                {
                    "messageId": "msg-027",
                    "from": "devansh.work@outlook.com",
                    "to": ["onboarding@company.com", "maya@client.com"],
                    "sentAt": "2026-05-04T09:35:00Z",
                    "body": "I will send the onboarding packet by Thursday morning with the architecture diagram, endpoint list, support contact, security notes, and source citation explanation.",
                },
                {
                    "messageId": "msg-028",
                    "from": "onboarding@company.com",
                    "to": ["devansh.work@outlook.com"],
                    "sentAt": "2026-05-05T11:50:00Z",
                    "body": "Great. Please also add a one-page quick start by Thursday evening for the customer success team.",
                },
            ],
        },
        {
            "threadId": "thr-009",
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "subject": "Contract Redlines and Approval Path",
            "participants": ["legal@company.com", "maya@client.com", "devansh.work@outlook.com"],
            "messages": [
                {
                    "messageId": "msg-029",
                    "from": "legal@company.com",
                    "to": ["devansh.work@outlook.com"],
                    "sentAt": "2026-05-05T09:05:00Z",
                    "body": "The client returned contract redlines. Please review the AI data processing clause and confirm whether the technical commitments are acceptable by Friday.",
                },
                {
                    "messageId": "msg-030",
                    "from": "maya@client.com",
                    "to": ["legal@company.com", "devansh.work@outlook.com"],
                    "sentAt": "2026-05-05T10:35:00Z",
                    "body": "Our legal team needs approval on the security exhibit before Friday evening. The contract can move to signature once that is approved.",
                },
                {
                    "messageId": "msg-031",
                    "from": "devansh.work@outlook.com",
                    "to": ["legal@company.com", "maya@client.com"],
                    "sentAt": "2026-05-05T12:15:00Z",
                    "body": "I will review the AI data processing clause and security exhibit tomorrow morning, then send approval notes before Friday evening.",
                },
                {
                    "messageId": "msg-032",
                    "from": "legal@company.com",
                    "to": ["devansh.work@outlook.com"],
                    "sentAt": "2026-05-06T08:30:00Z",
                    "body": "Please call out any blockers by Thursday afternoon. If there are no blockers, reply with approved language for the contract package.",
                },
            ],
        },
        {
            "threadId": "thr-010",
            "mailboxId": "mbx-outlook",
            "provider": "outlook",
            "subject": "Pilot Support Handoff",
            "participants": ["support@company.com", "pm@company.com", "devansh.work@outlook.com"],
            "messages": [
                {
                    "messageId": "msg-033",
                    "from": "support@company.com",
                    "to": ["devansh.work@outlook.com", "pm@company.com"],
                    "sentAt": "2026-05-06T10:00:00Z",
                    "body": "Before pilot handoff, please send the escalation contacts, expected response times, and known limitations by tomorrow morning.",
                },
                {
                    "messageId": "msg-034",
                    "from": "pm@company.com",
                    "to": ["support@company.com", "devansh.work@outlook.com"],
                    "sentAt": "2026-05-06T10:30:00Z",
                    "body": "Also include the launch deadline and the Friday customer check-in time in the support handoff notes.",
                },
                {
                    "messageId": "msg-035",
                    "from": "devansh.work@outlook.com",
                    "to": ["support@company.com", "pm@company.com"],
                    "sentAt": "2026-05-06T11:15:00Z",
                    "body": "I will send the support handoff notes by tomorrow morning with contacts, response times, limitations, launch deadline, and Friday check-in details.",
                },
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


def _bedrock_model_id():
    return os.environ.get("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL_ID)


def _embedding_model_id():
    return os.environ.get("EMBEDDING_MODEL_ID", DEFAULT_EMBEDDING_MODEL_ID)


def _bedrock_invoke_claude(prompt, max_tokens=900):
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
    )

    response = _bedrock.invoke_model(
        modelId=_bedrock_model_id(),
        body=body,
        accept="application/json",
        contentType="application/json",
    )
    payload = json.loads(response["body"].read())
    return "\n".join(
        part.get("text", "")
        for part in payload.get("content", [])
        if part.get("type") == "text" or "text" in part
    ).strip()


def _bedrock_embedding(text):
    response = _bedrock.invoke_model(
        modelId=_embedding_model_id(),
        body=json.dumps({"inputText": text}),
        accept="application/json",
        contentType="application/json",
    )
    payload = json.loads(response["body"].read())
    embedding = payload.get("embedding")
    if not embedding:
        raise ValueError("Bedrock embedding response did not include an embedding")
    return embedding


def _signed_opensearch_request(method, path, payload):
    base_url = (os.environ.get("OPENSEARCH_URL") or "").rstrip("/")
    if not base_url:
        raise ValueError("OPENSEARCH_URL is not configured")

    region = os.environ.get("APP_AWS_REGION") or os.environ.get("BEDROCK_REGION", "us-east-1")
    url = f"{base_url}{path}"
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    request = AWSRequest(method=method, url=url, data=body, headers=headers)
    credentials = boto3.Session().get_credentials()
    if credentials is None:
        raise ValueError("AWS credentials are not available for OpenSearch request signing")
    SigV4Auth(credentials.get_frozen_credentials(), "es", region).add_auth(request)

    prepared = request.prepare()
    http_request = urllib.request.Request(
        url=prepared.url,
        data=body,
        headers=dict(prepared.headers),
        method=method,
    )

    try:
        with urllib.request.urlopen(http_request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenSearch HTTP {exc.code}: {error_body}") from exc


def _signed_opensearch_post(path, payload):
    return _signed_opensearch_request("POST", path, payload)


def _opensearch_vector_sources(query, mailbox_id=None, top_k=5):
    index_name = os.environ.get("INDEX_NAME", "mailmanager-index")
    query_vector = _bedrock_embedding(query)

    filters = []
    if mailbox_id:
        filters.append({"term": {"mailboxId": mailbox_id}})

    search_body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {
                        "knn": {
                            "email_vector": {
                                "vector": query_vector,
                                "k": top_k,
                            }
                        }
                    }
                ],
                "filter": filters,
            }
        },
    }
    payload = _signed_opensearch_post(f"/{index_name}/_search", search_body)
    hits = payload.get("hits", {}).get("hits", [])

    sources = []
    for hit in hits[:top_k]:
        source = hit.get("_source", {})
        body = source.get("body") or source.get("content") or source.get("snippet", "")
        sources.append(
            {
                "threadId": source.get("threadId", ""),
                "messageId": source.get("messageId", hit.get("_id", "")),
                "mailboxId": source.get("mailboxId", mailbox_id or ""),
                "provider": source.get("provider", ""),
                "subject": source.get("subject", "Untitled email"),
                "sender": source.get("sender") or source.get("from", ""),
                "sentAt": source.get("sentAt", ""),
                "snippet": (source.get("snippet") or body)[:220],
                "score": hit.get("_score", 0),
            }
        )

    return [source for source in sources if source.get("threadId") or source.get("snippet")]


def _format_sources_for_prompt(sources):
    return "\n\n".join(
        [
            (
                f"Source {idx}: subject={source.get('subject')} sender={source.get('sender')} "
                f"sentAt={source.get('sentAt')}\n{(source.get('snippet') or '')[:180]}"
            )
            for idx, source in enumerate(sources[:3], start=1)
        ]
    )


def _thread_prompt_context(thread):
    lines = [f"Subject: {thread.get('subject', '')}"]
    for msg in thread.get("messages", [])[:3]:
        lines.append(
            (
                f"From: {msg.get('from', '')}\n"
                f"Sent: {msg.get('sentAt', '')}\n"
                f"Snippet: {(msg.get('body', '') or '')[:220]}"
            )
        )
    return "\n\n---\n\n".join(lines)


def _json_from_text(text):
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    if not match:
        raise ValueError("Bedrock response did not contain a JSON object")
    return json.loads(match.group(0))


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


TERM_GROUPS = {
    "approve": {"approve", "approved", "approves", "approval", "approvals", "approving"},
    "deadline": {"deadline", "deadlines", "due", "by", "before", "blocked", "blocker", "blockers"},
    "invoice": {"invoice", "invoices", "payment", "vendor", "payable"},
    "launch": {"launch", "launched", "review", "release"},
    "meeting": {"meeting", "schedule", "scheduled", "scheduling", "calendar", "invite", "kickoff"},
    "aws": {"aws", "gateway", "lambda", "dynamodb", "endpoint", "endpoints", "cloudops"},
    "security": {"security", "cors", "secrets", "pii", "iam", "retention"},
    "onboarding": {"onboarding", "handoff", "packet", "quickstart", "kickoff"},
    "contract": {"contract", "contracts", "redline", "redlines", "legal", "clause", "signature"},
}


ACTION_PATTERNS = [
    r"\bplease\s+([^.!?]+)",
    r"\bcan you\s+([^.!?]+)",
    r"\bcould we\s+([^.!?]+)",
    r"\bwe need\s+([^.!?]+)",
    r"\bneeds\s+([^.!?]+)",
    r"\bI will\s+([^.!?]+)",
]


DAY_PATTERN = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
TIME_PATTERN = r"morning|afternoon|evening|noon|at\s+noon|at\s+5\s*pm|[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)"
DUE_DATE_PATTERN = re.compile(
    rf"\b(?:by|before)\s+(?:(?:{DAY_PATTERN})(?:\s+(?:{TIME_PATTERN}))?|"
    rf"tomorrow(?:\s+(?:{TIME_PATTERN}))?|today|tonight|(?:{TIME_PATTERN}))\b|"
    rf"\b(?:{DAY_PATTERN})(?:\s+(?:{TIME_PATTERN}))?\b|"
    rf"\btomorrow(?:\s+(?:{TIME_PATTERN}))?\b",
    re.IGNORECASE,
)


def _tokens(text):
    return [t.lower() for t in re.findall(r"[a-zA-Z0-9]+", text or "")]


def _normalize_terms(text):
    normalized = set()
    for token in _tokens(text):
        matched = False
        for canonical, variants in TERM_GROUPS.items():
            if token in variants:
                normalized.add(canonical)
                normalized.update(variants)
                matched = True
                break
        if len(token) <= 2:
            continue
        if not matched:
            normalized.add(token)
    return normalized


def _sentences(messages):
    items = []
    for msg in messages:
        for sentence in re.split(r"(?<=[.!?])\s+", msg.get("body", "")):
            sentence = sentence.strip()
            if sentence:
                items.append((msg, sentence))
    return items


def _extract_due_date(text):
    matches = DUE_DATE_PATTERN.findall(text or "")
    if not matches:
        return "Check email context"

    cleaned = []
    for match in matches:
        value = match if isinstance(match, str) else match[0]
        value = re.sub(r"\s+", " ", value.strip())
        if value and value.lower() not in [item.lower() for item in cleaned]:
            cleaned.append(value)
    return ", ".join(cleaned[:2]) if cleaned else "Check email context"


def _extract_task(text):
    for pattern in ACTION_PATTERNS:
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if match:
            task = match.group(1).strip(" ,")
            return task[:1].upper() + task[1:]
    return (text or "").strip()[:160]


def _priority_for(text):
    lower = (text or "").lower()
    if any(term in lower for term in ["blocked", "blocker", "deadline", "by friday", "tomorrow"]):
        return "high"
    if any(term in lower for term in ["please", "need", "review", "confirm", "approve"]):
        return "medium"
    return "low"


def _keyword_sources(query, mailbox_id=None):
    terms = _normalize_terms(query)
    messages = _all_messages(_get_table(), mailbox_id)

    scored = []
    for msg in messages:
        text = f"{msg.get('subject', '')} {msg.get('body', '')}"
        searchable = _normalize_terms(text)
        exact_text = text.lower()
        score = len(searchable.intersection(terms)) * 3
        score += sum(exact_text.count(term) for term in terms if len(term) > 3)

        if score > 0:
            scored.append((score, msg))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]

    return [
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


def _template_search_answer(sources):
    if not sources:
        return "I could not find enough evidence in the selected mailbox to answer that."

    top_points = [
        f"{src['subject']}: {src['snippet']}"
        for src in sources[:3]
    ]
    return "Based on the matching emails:\n- " + "\n- ".join(top_points)


def _bedrock_search_answer(query, sources):
    context = _format_sources_for_prompt(sources)
    prompt = f"""
Answer using only these email snippets. Be concise and cite source subjects when useful.

Question:
{query}

Sources:
{context}
"""
    return _bedrock_invoke_claude(prompt, max_tokens=250)


def _template_summary_payload(thread):
    messages = thread["messages"]
    sentence_items = _sentences(messages)
    key_points = [sentence for _, sentence in sentence_items[:4]]
    action_candidates = [
        sentence
        for _, sentence in sentence_items
        if any(term in sentence.lower() for term in ["please", "need", "confirm", "approve", "send", "review", "prepare"])
    ]
    next_step = _extract_task(action_candidates[-1] if action_candidates else messages[-1].get("body", ""))
    return {
        "short": f"{thread['subject']} is active with {len(messages)} messages and clear follow-up needed.",
        "keyPoints": key_points[:4],
        "nextStep": next_step,
        "openQuestions": [f"Next step: {next_step}"],
    }


def _bedrock_summary_payload(thread):
    prompt = f"""
Summarize this email thread. Return ONLY compact JSON:
{{
  "short": "one sentence",
  "keyPoints": ["point 1", "point 2"],
  "nextStep": "one next step",
  "openQuestions": ["open issue"]
}}

Thread snippets:
{_thread_prompt_context(thread)}
"""
    text = _bedrock_invoke_claude(prompt, max_tokens=250)
    payload = _json_from_text(text)
    return {
        "short": str(payload.get("short", "")).strip() or f"This thread is about {thread['subject']}.",
        "keyPoints": payload.get("keyPoints") if isinstance(payload.get("keyPoints"), list) else [],
        "nextStep": str(payload.get("nextStep", "")).strip() or "Confirm the next step from the thread.",
        "openQuestions": payload.get("openQuestions") if isinstance(payload.get("openQuestions"), list) else [],
    }


def _template_draft_reply(thread, intent):
    subject = thread["subject"]
    action_items = json.loads(_action_items(_get_table(), thread["threadId"])["body"]).get("actionItems", [])
    next_action = action_items[0]["task"] if action_items else intent
    return (
        f"Hi,\n\nThanks for the update on {subject}. I have the next step captured: "
        f"{next_action}. I will follow up with the requested details and flag any blockers as soon as I find them.\n\n"
        "Please let me know if there is a specific format or stakeholder list you want me to use.\n\n"
        "Best,\nDevansh"
    )


def _bedrock_draft_reply(thread, intent):
    prompt = f"""
Draft a concise professional email reply. Preserve normal email line breaks.
Intent: {intent}

Thread snippets:
{_thread_prompt_context(thread)}
"""
    return _bedrock_invoke_claude(prompt, max_tokens=250)


def _search(table, event):
    body = _parse_body(event)
    query = body.get("query", "").strip()
    mailbox_id = body.get("mailboxId")

    if not query:
        return _response(400, {"error": "missing_query"})

    retrieval_mode = "keyword-fallback"
    sources = []

    try:
        sources = _opensearch_vector_sources(query, mailbox_id)
        if sources:
            retrieval_mode = "opensearch-vector"
        else:
            logger.info("OpenSearch vector retrieval returned no results; using keyword fallback")
    except Exception as exc:
        logger.exception("OpenSearch vector retrieval failed; using keyword fallback: %s", exc)

    if not sources:
        sources = _keyword_sources(query, mailbox_id)

    model = "template"
    try:
        if sources:
            answer = _bedrock_search_answer(query, sources)
            if answer:
                model = "bedrock"
            else:
                raise ValueError("Bedrock returned an empty search answer")
        else:
            answer = _template_search_answer(sources)
    except Exception as exc:
        logger.exception("Bedrock search generation failed; using template fallback: %s", exc)
        answer = _template_search_answer(sources)

    return _response(
        200,
        {
            "query": query,
            "answer": answer,
            "sources": sources,
            "retrievalMode": retrieval_mode,
            "model": model,
        },
    )


def _summary(table, thread_id):
    thread_resp = json.loads(_get_thread(table, thread_id)["body"])
    if "error" in thread_resp:
        return _response(404, thread_resp)

    thread = thread_resp["thread"]
    model = "template"

    try:
        summary = _bedrock_summary_payload(thread)
        model = "bedrock"
    except Exception as exc:
        logger.exception("Bedrock summary generation failed; using template fallback: %s", exc)
        summary = _template_summary_payload(thread)

    return _response(
        200,
        {
            "threadId": thread_id,
            "summary": summary,
            "model": model,
        },
    )


def _draft_reply(table, thread_id, event):
    body = _parse_body(event)
    intent = body.get("intent", "acknowledge and confirm next steps")

    thread_resp = json.loads(_get_thread(table, thread_id)["body"])
    if "error" in thread_resp:
        return _response(404, thread_resp)

    thread = thread_resp["thread"]
    model = "template"

    try:
        draft = _bedrock_draft_reply(thread, intent)
        if not draft:
            raise ValueError("Bedrock returned an empty draft reply")
        model = "bedrock"
    except Exception as exc:
        logger.exception("Bedrock draft reply generation failed; using template fallback: %s", exc)
        draft = _template_draft_reply(thread, intent)

    return _response(
        200,
        {
            "threadId": thread_id,
            "draft": draft,
            "model": model,
        },
    )


def _action_items(table, thread_id):
    thread_resp = json.loads(_get_thread(table, thread_id)["body"])
    if "error" in thread_resp:
        return _response(404, thread_resp)

    action_items = []
    messages = thread_resp["thread"]["messages"]

    keywords = ["please", "need", "approve", "approval", "send", "prepare", "confirm", "review", "schedule", "include"]
    for msg in messages:
        body = msg.get("body", "")
        lower = body.lower()
        if any(k in lower for k in keywords):
            task = _extract_task(body)
            action_items.append(
                {
                    "task": task[:160],
                    "owner": "Devansh",
                    "dueDate": _extract_due_date(body),
                    "priority": _priority_for(body),
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


def _setup_index():
    index_name = os.environ.get("INDEX_NAME", "mailmanager-index")
    mapping = {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "email_vector": {"type": "knn_vector", "dimension": 1536},
                "threadId":     {"type": "keyword"},
                "messageId":    {"type": "keyword"},
                "mailboxId":    {"type": "keyword"},
                "subject":      {"type": "text"},
                "sender":       {"type": "keyword"},
                "sentAt":       {"type": "date"},
                "snippet":      {"type": "text"},
                "body":         {"type": "text"},
            }
        },
    }
    try:
        result = _signed_opensearch_request("PUT", f"/{index_name}", mapping)
        return _response(200, {"status": "created", "index": index_name, "detail": result})
    except RuntimeError as exc:
        msg = str(exc)
        if "resource_already_exists_exception" in msg:
            return _response(200, {"status": "already_exists", "index": index_name})
        return _response(500, {"error": msg})


def _generate_reply(event):
    body = _parse_body(event)
    subject = (body.get("subject") or "(no subject)").strip()
    sender_name = (body.get("senderName") or "Unknown").strip()
    sender_email = (body.get("senderEmail") or "").strip()
    body_text = (body.get("bodyText") or "").strip()
    thread_history = body.get("threadHistory") or []
    tone = body.get("tone") or "professional"

    if not body_text and not subject:
        return _response(400, {"error": "missing_content"})

    # RAG: pull relevant inbox context from OpenSearch to ground the reply
    retrieval_mode = "none"
    retrieved_count = 0
    rag_context = ""
    try:
        query = f"{subject} {body_text[:300]}"
        sources = _opensearch_vector_sources(query, top_k=3)
        if sources:
            retrieval_mode = "opensearch-vector"
            retrieved_count = len(sources)
            rag_context = _format_sources_for_prompt(sources)
        else:
            logger.info("/reply: OpenSearch returned no results; skipping RAG context")
    except Exception as exc:
        logger.exception("/reply: OpenSearch retrieval failed; proceeding without RAG context: %s", exc)

    tone_instruction = {
        "professional": "Write a professional and polished reply.",
        "casual": "Write a friendly and casual reply.",
        "brief": "Write a very short and direct reply (2-3 sentences max).",
    }.get(tone, "Write a professional reply.")

    history_section = ""
    if thread_history:
        history_section = (
            "\n\nEarlier messages in this thread (oldest first):\n"
            + "\n\n".join(f"[{i + 1}] {msg}" for i, msg in enumerate(thread_history[:5]))
        )

    rag_section = f"\n\nRelevant context from inbox:\n{rag_context}" if rag_context else ""

    prompt = (
        f"You are drafting an email reply on behalf of the user."
        f"{history_section}{rag_section}\n\n"
        f"Email to reply to:\n"
        f"From: {sender_name} <{sender_email}>\n"
        f"Subject: {subject}\n\n"
        f"{body_text}\n\n"
        f"---\n"
        f"{tone_instruction} Output only the reply text, no subject line, no greeting label."
    )

    model = "template"
    reply_text = ""
    try:
        reply_text = _bedrock_invoke_claude(prompt, max_tokens=512)
        if reply_text:
            model = "bedrock"
        else:
            raise ValueError("Bedrock returned empty reply")
    except Exception as exc:
        logger.exception("/reply: Bedrock generation failed; using template fallback: %s", exc)
        reply_text = (
            f"Hi {sender_name},\n\n"
            f"Thank you for your email regarding {subject}. "
            f"I will review the details and follow up with you shortly.\n\n"
            "Best regards"
        )

    return _response(
        200,
        {
            "replyText": reply_text,
            "modelUsed": _bedrock_model_id(),
            "truncated": False,
            "retrievedCount": retrieved_count,
            "retrievalMode": retrieval_mode,
            "model": model,
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

    if method == "POST" and path == "/admin/setup-index":
        return _setup_index()

    if method == "POST" and path == "/reply":
        return _generate_reply(event)

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
