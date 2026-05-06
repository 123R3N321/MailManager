# Mail Manager

Mail Manager is a cloud-based Email RAG SaaS demo that helps users search email threads, summarize conversations, generate draft replies, and extract action items.

==================================================
FEATURES
==================================================

- Gmail and Outlook demo inbox switching
- Email thread viewer
- Natural-language inbox search
- Search answers with source emails
- Thread summaries
- Draft reply generation
- Action item extraction
- AWS-hosted frontend and backend

==================================================
ARCHITECTURE
==================================================

Frontend Flow:

S3 Static Website → API Gateway → Lambda → DynamoDB / S3 / SQS

AWS Services Used:

1. Amazon S3
- Hosts frontend website
- Stores raw demo email JSON

2. API Gateway
- Exposes backend HTTP API endpoints

3. AWS Lambda
- Handles backend API logic
- Search handling
- Summary generation
- Draft reply generation
- Action item extraction

4. DynamoDB
- Stores mailbox metadata
- Stores email threads/messages

5. Amazon SQS
- Async ingestion queue scaffold

6. CloudWatch
- Logging and monitoring

7. Secrets Manager
- Placeholder OAuth secret storage

==================================================
HOSTED URLS
==================================================

Frontend:
http://mailmanager-demo-frontend-devansh.s3-website-us-east-1.amazonaws.com

Backend API:
https://2jnfchgyjb.execute-api.us-east-1.amazonaws.com/

==================================================
LOCAL DEVELOPMENT
==================================================

Run locally:

cd frontend
npm install
npm run dev

Create frontend/.env:

VITE_API_BASE_URL=https://2jnfchgyjb.execute-api.us-east-1.amazonaws.com/

==================================================
BUILD FRONTEND
==================================================

cd frontend
npm run build

==================================================
DEPLOY FRONTEND
==================================================

aws s3 sync dist/ s3://mailmanager-demo-frontend-devansh --delete

==================================================
SEED DEMO DATA
==================================================

API_URL="https://2jnfchgyjb.execute-api.us-east-1.amazonaws.com/"

curl -sS -X POST "${API_URL}ingest/demo" | jq .

==================================================
EXAMPLE API CALLS
==================================================

Get Mailboxes:

curl -sS "${API_URL}mailboxes" | jq .

Get Threads:

curl -sS "${API_URL}threads?mailboxId=mbx-gmail" | jq .

Search Inbox:

curl -sS -X POST "${API_URL}search" \
  -H "Content-Type: application/json" \
  -d '{"query":"what approvals are pending","mailboxId":"mbx-gmail"}' | jq .

Generate Summary:

curl -sS -X POST "${API_URL}threads/thr-001/summary" | jq .

Generate Draft Reply:

curl -sS -X POST "${API_URL}threads/thr-001/draft-reply" \
  -H "Content-Type: application/json" \
  -d '{"intent":"confirm approval timing"}' | jq .

Extract Action Items:

curl -sS -X POST "${API_URL}threads/thr-001/action-items" | jq .

==================================================
CURRENT MVP STATUS
==================================================

Implemented:

- AWS-hosted frontend
- AWS API backend
- Gmail/Outlook demo inbox switching
- Email thread viewer
- Search with source emails
- Template-based summaries
- Template-based draft replies
- Template-based action item extraction
- Terraform infrastructure deployment

==================================================
PLANNED IMPROVEMENTS
==================================================

Amazon Bedrock:
- Real LLM-powered summaries
- Smart replies
- AI action item extraction

OpenSearch:
- Semantic/vector search
- Better RAG retrieval pipeline

OAuth Integration:
- Real Gmail linking
- Real Outlook linking

Authentication:
- Cognito-based authentication

==================================================
NOTES
==================================================

This project is currently an MVP/demo implementation focused on:

- Cloud-native SaaS architecture
- Serverless AWS backend design
- Email retrieval workflows
- RAG-style email intelligence concepts

Current implementation uses:
- keyword fallback retrieval
- template-based AI responses

Future production architecture would integrate:
- Amazon Bedrock
- OpenSearch vector retrieval
- Real OAuth mailbox integration
- Production-grade authentication