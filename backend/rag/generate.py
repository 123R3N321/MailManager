import json
import os
import boto3

_client = None

def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _client


def generate_reply(current_email: dict, similar_emails: list[dict],
                   tone: str = "professional") -> dict:
    """Build a RAG prompt from retrieved context and call Bedrock Claude."""
    model_id = os.environ.get("CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    prompt = _build_prompt(current_email, similar_emails, tone)

    response = _bedrock().invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0.7,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    body = json.loads(response["body"].read())
    reply_text = body["content"][0]["text"]
    stop_reason = body.get("stop_reason", "")

    return {
        "replyText":      reply_text,
        "modelUsed":      model_id,
        "retrievedCount": len(similar_emails),
        "truncated":      stop_reason == "max_tokens",
    }


def _build_prompt(email: dict, context: list[dict], tone: str) -> str:
    tone_instruction = {
        "professional": "Write a professional and polished reply.",
        "casual":       "Write a friendly and casual reply.",
        "brief":        "Write a very short and direct reply (2-3 sentences max).",
    }.get(tone, "Write a professional reply.")

    # ── RAG context block ──────────────────────────────────────────────────
    # This is the core of RAG: retrieved similar emails are injected here so
    # the model can mirror the user's existing communication style and domain
    # vocabulary, rather than generating a generic response.
    context_block = ""
    if context:
        lines = ["\n=== SIMILAR PAST EMAILS (style/domain context) ==="]
        for i, item in enumerate(context, 1):
            snippet = item["body_text"][:400].replace("\n", " ")
            lines.append(
                f"\n[{i}] From: {item['sender_name']} | "
                f"Subject: {item['subject']}\n{snippet}"
            )
        context_block = "\n".join(lines) + "\n"

    thread_block = ""
    if email.get("threadHistory"):
        thread_block = "\n=== EARLIER MESSAGES IN THIS THREAD ===\n"
        for i, msg in enumerate(email["threadHistory"], 1):
            thread_block += f"\n[{i}] {msg[:400]}\n"

    return (
        f"You are drafting an email reply on behalf of the user."
        f"{context_block}"
        f"{thread_block}"
        f"\n=== EMAIL TO REPLY TO ==="
        f"\nFrom: {email['senderName']} <{email['senderEmail']}>"
        f"\nSubject: {email['subject']}"
        f"\n\n{email['bodyText']}"
        f"\n\n---"
        f"\n{tone_instruction} Output only the reply text, no subject line, no greeting label."
    )
