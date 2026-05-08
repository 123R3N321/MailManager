import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import boto3

_table = None

def _get_table():
    global _table
    if _table is None:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        _table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
    return _table


def save_email(subject: str, sender_name: str, sender_email: str,
               body_text: str, embedding: list[float]) -> str:
    """Store an email + its embedding vector. Returns the generated id."""
    item_id = str(uuid.uuid4())
    # DynamoDB requires Decimal for numbers; convert the float list
    decimal_embedding = [Decimal(str(round(v, 8))) for v in embedding]

    _get_table().put_item(Item={
        "id":           item_id,
        "subject":      subject,
        "sender_name":  sender_name,
        "sender_email": sender_email,
        "body_text":    body_text[:2000],   # cap storage size
        "embedding":    decimal_embedding,
        "created_at":   datetime.now(timezone.utc).isoformat(),
    })
    return item_id


def find_similar(query_embedding: list[float], top_k: int = 3,
                 exclude_id: str | None = None) -> list[dict]:
    """
    Full-table scan + cosine similarity (dot product of unit-normalized vectors).
    Appropriate for academic scale (<1 000 emails). At larger scale, replace
    with OpenSearch or pgvector ANN index.
    """
    table = _get_table()
    items = []
    scan_kwargs = {
        "ProjectionExpression": "id, subject, sender_name, body_text, embedding",
    }

    # Paginate through the full table
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    # Skip the email we just ingested so it doesn't retrieve itself
    if exclude_id:
        items = [i for i in items if i["id"] != exclude_id]

    if not items:
        return []

    # Score every item
    scored = []
    for item in items:
        stored_vec = [float(v) for v in item["embedding"]]
        score = _dot(query_embedding, stored_vec)   # both normalized → equals cosine sim
        scored.append({
            "score":       score,
            "subject":     item.get("subject", ""),
            "sender_name": item.get("sender_name", ""),
            "body_text":   item.get("body_text", ""),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
