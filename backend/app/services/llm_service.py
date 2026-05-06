from app.core.aws_config import get_bedrock_client
from app.services.vector_db import VectorDBService
import json

class LLMService:
    def __init__(self):
        self.bedrock = get_bedrock_client()
        self.vector_db = VectorDBService()

    def generate_rag_summary(self, user_id, mailbox_id, query):
        """The main RAG pipeline: Retrieve context, then generate summary."""
        
        # 1. Retrieve context from OpenSearch
        context_chunks = self.vector_db.query_relevant_emails(query, mailbox_id)
        context_text = "\n---\n".join(context_chunks)

        # 2. Construct the Prompt
        prompt = f"""
        Human: Use the following email snippets to answer: {query}
        
        Context:
        {context_text}
        
        Assistant:"""

        # 3. Invoke Claude 3 on Bedrock
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        })

        response = self.bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=body
        )
        
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
