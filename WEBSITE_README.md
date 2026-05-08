# Mail Manager

Mail Manager is a cloud-based Email RAG SaaS demo that helps users search email threads, summarize conversations, generate draft replies, and extract action items.

---

# Features

- Gmail and Outlook demo inbox switching
- Email thread viewer
- Natural-language inbox search
- Search answers with source emails
- Thread summaries
- Draft reply generation
- Action item extraction
- AWS-hosted frontend and backend

---

# Architecture

Frontend Flow:

```text
S3 Static Website → API Gateway → Lambda → DynamoDB / S3 / SQS
```

## AWS Services Used

### Amazon S3
- Hosts frontend website
- Stores raw demo email JSON

### API Gateway
- Exposes backend HTTP API endpoints

### AWS Lambda
- Handles backend API logic
- Search handling
- Summary generation
- Draft reply generation
- Action item extraction

### DynamoDB
- Stores mailbox metadata
- Stores email threads/messages

### Amazon SQS
- Async ingestion queue scaffold

### CloudWatch
- Logging and monitoring

### Secrets Manager
- Placeholder OAuth secret storage

---

# Hosted URLs

## Frontend

```text
http://mailmanager-demo-frontend-devansh.s3-website-us-east-1.amazonaws.com
```

## Backend API

```text
https://2jnfchgyjb.execute-api.us-east-1.amazonaws.com/
```

---

# Local Development

Run locally:

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env`:

```bash
VITE_API_BASE_URL=https://2jnfchgyjb.execute-api.us-east-1.amazonaws.com/
```

---

# Build Frontend

```bash
cd frontend
npm run build
```

---

# Deploy Frontend

```bash
aws s3 sync dist/ s3://mailmanager-demo-frontend-devansh --delete
```

---

# Seed Demo Data

```bash
API_URL="https://2jnfchgyjb.execute-api.us-east-1.amazonaws.com/"

curl -sS -X POST "${API_URL}ingest/demo" | jq .
```

---

# Example API Calls

## Get Mailboxes

```bash
curl -sS "${API_URL}mailboxes" | jq .
```

## Get Threads

```bash
curl -sS "${API_URL}threads?mailboxId=mbx-gmail" | jq .
```

## Search Inbox

```bash
curl -sS -X POST "${API_URL}search" \
  -H "Content-Type: application/json" \
  -d '{"query":"what approvals are pending","mailboxId":"mbx-gmail"}' | jq .
```

## Generate Summary

```bash
curl -sS -X POST "${API_URL}threads/thr-001/summary" | jq .
```

## Generate Draft Reply

```bash
curl -sS -X POST "${API_URL}threads/thr-001/draft-reply" \
  -H "Content-Type: application/json" \
  -d '{"intent":"confirm approval timing"}' | jq .
```

## Extract Action Items

```bash
curl -sS -X POST "${API_URL}threads/thr-001/action-items" | jq .
```

---

# Current MVP Status

## Implemented

- AWS-hosted frontend
- AWS API backend
- Gmail/Outlook demo inbox switching
- Email thread viewer
- Search with source emails
- Template-based summaries
- Template-based draft replies
- Template-based action item extraction
- Terraform infrastructure deployment

---

# Planned Improvements

## Amazon Bedrock
- Real LLM-powered summaries
- Smart replies
- AI action item extraction

## OpenSearch
- Semantic/vector search
- Better RAG retrieval pipeline

## OAuth Integration
- Real Gmail linking
- Real Outlook linking

## Authentication
- Cognito-based authentication

---

# Notes

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