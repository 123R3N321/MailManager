"""
Lambda entry point. Routes POST /ingest and POST /reply.

POST /ingest  — embed an email and store it in DynamoDB for future RAG retrieval
POST /reply   — find similar past emails, build RAG prompt, call Bedrock Claude
"""
import json
from rag.embed import get_embedding
from rag.store import save_email, find_similar
from rag.generate import generate_reply


def lambda_handler(event, _context):
    route = event.get("routeKey", "")
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _resp(400, {"error": "Invalid JSON body"})

    try:
        if route == "POST /ingest":
            return _resp(200, _handle_ingest(body))
        if route == "POST /reply":
            return _resp(200, _handle_reply(body))
        return _resp(404, {"error": f"Unknown route: {route}"})
    except Exception as exc:   # noqa: BLE001
        print(f"ERROR [{route}]: {exc}")
        return _resp(500, {"error": str(exc)})


# ── handlers ──────────────────────────────────────────────────────────────────

def _handle_ingest(body: dict) -> dict:
    required = ("subject", "senderName", "senderEmail", "bodyText")
    missing = [f for f in required if not body.get(f)]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    embedding = get_embedding(body["bodyText"])
    item_id = save_email(
        subject=body["subject"],
        sender_name=body["senderName"],
        sender_email=body["senderEmail"],
        body_text=body["bodyText"],
        embedding=embedding,
    )
    return {"success": True, "id": item_id}


def _handle_reply(body: dict) -> dict:
    required = ("subject", "senderName", "senderEmail", "bodyText")
    missing = [f for f in required if not body.get(f)]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    # 1. Embed the incoming email
    query_embedding = get_embedding(body["bodyText"])

    # 2. Store it so it's available for future RAG lookups
    item_id = save_email(
        subject=body["subject"],
        sender_name=body["senderName"],
        sender_email=body["senderEmail"],
        body_text=body["bodyText"],
        embedding=query_embedding,
    )

    # 3. Retrieve the top-3 most similar past emails (excluding the one just stored)
    similar = find_similar(query_embedding, top_k=3, exclude_id=item_id)

    # 4. Generate a reply using the retrieved context + Bedrock Claude
    tone = body.get("tone", "professional")
    result = generate_reply(body, similar, tone)
    return result


# ── helpers ───────────────────────────────────────────────────────────────────

def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
