from app.core.aws_config import get_opensearch_client, get_bedrock_client
import json

class VectorDBService:
    def __init__(self):
        self.os_client = get_opensearch_client()
        self.bedrock = get_bedrock_client()

    def _get_embedding(self, text):
        """Converts text to a 1536-dimension vector using Amazon Titan."""
        body = json.dumps({"inputText": text})
        response = self.bedrock.invoke_model(
            body=body,
            modelId="amazon.titan-embed-text-v1"
        )
        return json.loads(response['body'].read())['embedding']

    def query_relevant_emails(self, user_query, mailbox_id, top_k=5):
        """Performs a k-NN search to find the most relevant context."""
        query_vector = self._get_embedding(user_query)
        
        search_body = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": [
                        {"knn": {"email_vector": {"vector": query_vector, "k": top_k}}}
                    ],
                    "filter": [{"term": {"mailbox_id": mailbox_id}}] # Tenant isolation
                }
            }
        }
        response = self.os_client.search(index="email-index", body=search_body)
        return [hit['_source']['content'] for hit in response['hits']['hits']]
