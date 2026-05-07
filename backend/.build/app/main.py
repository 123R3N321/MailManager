import logging
from fastapi import FastAPI, Body, HTTPException
from mangum import Mangum
from app.services.llm_service import LLMService
from app.services.vector_db import VectorDBService

app = FastAPI(title="MailManager AI-RAG")

@app.get("/health")
async def health_check():
    # This will now always succeed even if OpenSearch is down
    return {"status": "healthy", "version": "v1.1-rag"}

@app.post("/search")
async def search_inbox(payload: dict = Body(...)):
    # Initialize only when this specific route is called
    vector_service = VectorDBService()
    
    query = payload.get("query")
    mailbox_id = payload.get("mailboxId")
    
    if not query or not mailbox_id:
        raise HTTPException(status_code=400, detail="Missing query or mailboxId")

    results = await vector_service.query_relevant_emails(query, mailbox_id)
    return {"results": results}

@app.post("/threads/{thread_id}/summary")
async def generate_summary(thread_id: str, mailboxId: str = None):
    # Initialize only when this specific route is called
    ai_service = LLMService()
    try:
        summary = await ai_service.generate_rag_summary(thread_id, mailboxId, "Summarize this.")
        return {"thread_id": thread_id, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

handler = Mangum(app, lifespan="off", api_gateway_base_path=None)
