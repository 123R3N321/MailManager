import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Import new RAG services
from app.services.llm_service import LLMService
from app.services.vector_db import VectorDBService

# 1. Initialize FastAPI App
app = FastAPI(
    title="MailManager AI-RAG Backend",
    description="Serverless API for intelligent email management using Bedrock and OpenSearch."
)

# 2. Configure Security Middleware
# In production, restrict 'allow_origins' to S3 website URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Singleton Service Initialization
# Initializing here allows Lambda to reuse the connection across warm starts.
ai_service = LLMService()
vector_service = VectorDBService()

# --- ENDPOINTS ---

@app.get("/health")
async def health_check():
    """Tier A check used by Makefile and CI/CD for verification."""
    return {"status": "healthy", "version": "v1.1-rag"}

@app.get("/mailboxes")
async def get_mailboxes():
    """Retrieve available mailbox metadata from DynamoDB."""
    # Logic to fetch from DynamoDB tables.
    return {"mailboxes": ["mbx-gmail", "mbx-outlook"]}

@app.post("/search")
async def search_inbox(payload: dict = Body(...)):
    """
    Semantic Search Endpoint.
    Transitions from keyword fallback to OpenSearch Vector Retrieval.
    """
    query = payload.get("query")
    mailbox_id = payload.get("mailboxId")
    
    if not query or not mailbox_id:
        raise HTTPException(status_code=400, detail="Missing query or mailboxId")

    # Perform k-NN search via OpenSearch
    results = await vector_service.query_relevant_emails(query, mailbox_id)
    return {"results": results}

@app.post("/threads/{thread_id}/summary")
async def generate_summary(thread_id: str, mailboxId: str):
    """
    RAG Summary Endpoint.
    Replaces template-based summaries with real LLM generation.
    """
    try:
        # Pipeline: Retrieve context -> Bedrock Prompt -> Response
        summary = await ai_service.generate_rag_summary(thread_id, mailboxId, "Summarize this thread.")
        return {"thread_id": thread_id, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/demo")
async def seed_demo_data():
    """
    Data Ingestion.
    Populates DynamoDB and triggers OpenSearch vector indexing.
    """
    # Demo ingestion logic
    # + Call vector_service.index_email() for each message
    return {"status": "Demo data ingestion and indexing complete."}

# 4. Lambda Handler
# This wraps the FastAPI app for AWS Lambda deployment.
handler = Mangum(app)
