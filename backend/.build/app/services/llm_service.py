from app.core.aws_config import get_bedrock_client
from app.services.vector_db import VectorDBService
import json
import os

class LLMService:
    def __init__(self):
        self.bedrock = get_bedrock_client()
        self.vector_db = VectorDBService()
        # Use environment variable from lambda.tf with a fallback
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

    def generate_rag_summary(self, thread_id, mailbox_id, query):
        """The main RAG pipeline: Retrieve context, then generate summary."""
        
        # 1. Retrieve context from OpenSearch
        # Note: Ensure vector_db.py is also updated to use INDEX_NAME env var
        context_chunks = self.vector_db.query_relevant_emails(query, mailbox_id)
        
        if not context_chunks:
            context_text = "No relevant email context found."
        else:
            context_text = "\n---\n".join(context_chunks)

        # 2. Construct the Prompt (Anthropic Message format)
        # Note: Do not use 'Human:' or 'Assistant:' prefixes inside the content 
        # when using the 'messages' API; use the role structure instead.
        prompt_content = f"""Use the following email snippets to answer the user query.
        
        Context:
        {context_text}
        
        User Query: {query}"""

        # 3. Invoke Claude 3 on Bedrock
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user", 
                    "content": [{"type": "text", "text": prompt_content}]
                }
            ]
        })

        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            # Propagate or log the error for CloudWatch
            print(f"Error invoking Bedrock model {self.model_id}: {str(e)}")
            raise e
