import json
import boto3

_client = None

def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _client

def get_embedding(text: str, model_id: str = "amazon.titan-embed-text-v2:0") -> list[float]:
    """Embed text using Amazon Titan Embeddings V2 (512 dimensions, normalized)."""
    truncated = text[:8000]  # Titan V2 input limit ~8192 tokens
    response = _bedrock().invoke_model(
        modelId=model_id,
        body=json.dumps({
            "inputText": truncated,
            "dimensions": 512,
            "normalize": True,   # unit-normalized → dot product == cosine similarity
        }),
    )
    body = json.loads(response["body"].read())
    return body["embedding"]
