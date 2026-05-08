# Design Document — Gmail AI Reply

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (Chrome Extension)                                     │
│                                                                 │
│  Gmail DOM  ──►  content.js  ──────────────────────────────┐   │
│  (read email,    (MutationObserver,                         │   │
│   inject btn)    extract email context)                     │   │
│                          │ chrome.runtime.sendMessage       │   │
│                          ▼                                  │   │
│               background.js (service worker)                │   │
│               ├── dummy provider  (local mock)              │   │
│               ├── claude provider (direct Anthropic API)    │   │
│               ├── openai provider (direct OpenAI API)       │   │
│               └── aws-backend provider ────────────────┐    │   │
└────────────────────────────────────────────────────────┼────┘   
                                                         │ HTTPS POST
┌────────────────────────────────────────────────────────┼────────┐
│  AWS (us-east-1)                                        │        │
│                                                         ▼        │
│  API Gateway (HTTP API v2)  ──►  Lambda (Python 3.12)           │
│  POST /ingest                    handler.py                      │
│  POST /reply                     ├── rag/embed.py               │
│                                  ├── rag/store.py               │
│                                  └── rag/generate.py            │
│                                        │           │             │
│                                        ▼           ▼             │
│                                   DynamoDB    Amazon Bedrock     │
│                                (email store)  ├── Titan Embed V2 │
│                                               └── Claude 3 Haiku │
└─────────────────────────────────────────────────────────────────┘
```

## 2. RAG Pipeline — Step by Step

RAG (Retrieval-Augmented Generation) grounds Claude's reply in the user's own
email history instead of producing a generic response.

```
Incoming email
     │
     │  1. EMBED
     ▼
Titan Embeddings V2
     │  512-dimensional unit-normalized vector
     │
     │  2. STORE  (side effect — builds the corpus over time)
     ▼
DynamoDB  ──  {id, subject, sender, body_text, embedding, created_at}
     │
     │  3. RETRIEVE  (full-table scan + dot-product similarity)
     ▼
Top-3 most similar past emails
     │
     │  4. AUGMENT  (inject retrieved context into the prompt)
     ▼
┌──────────────────────────────────────────────────────┐
│  PROMPT                                              │
│  === SIMILAR PAST EMAILS (style reference) ===       │
│  [1] From: Alice | Subject: Q3 planning …            │
│  [2] From: Bob   | Subject: Budget review …          │
│                                                      │
│  === EMAIL TO REPLY TO ===                           │
│  From: Carol <carol@example.com>                     │
│  Subject: Follow-up on proposal                      │
│  …body…                                              │
│                                                      │
│  Write a professional reply.                         │
└──────────────────────────────────────────────────────┘
     │
     │  5. GENERATE
     ▼
Claude 3 Haiku (via Bedrock)
     │
     ▼
Generated reply  ──►  extension modal  ──►  user copies to Gmail
```

**Why dot product instead of full cosine similarity?**
Titan Embeddings V2 with `normalize=True` returns unit vectors, so
`dot(a, b) == cosine_similarity(a, b)`. The dot product avoids the extra
sqrt computation for every stored vector.

**Why full-table scan instead of an ANN index?**
For <1 000 emails, a Python loop over 512 floats × N items runs in <50 ms
inside Lambda. OpenSearch Serverless (the AWS ANN option) has a $350+/month
minimum even with zero traffic — unacceptable for an academic push-button
deploy/destroy setup. The upgrade path is documented in §7.

## 3. DynamoDB Schema

Table name: `gmail-ai-reply-emails`  
Billing: `PAY_PER_REQUEST` (zero idle cost)

| Attribute     | Type            | Notes                                   |
|---------------|-----------------|------------------------------------------|
| `id`          | String (PK)     | UUID v4                                  |
| `subject`     | String          | Email subject line                       |
| `sender_name` | String          | Display name of sender                   |
| `sender_email`| String          | Sender email address                     |
| `body_text`   | String          | Plain text, capped at 2 000 characters   |
| `embedding`   | List of Decimal | 512 floats stored as Decimal (DynamoDB)  |
| `created_at`  | String          | ISO-8601 UTC timestamp                   |

No GSI or sort key. All queries are full-table scans — intentional trade-off
for simplicity at academic scale.

Item size estimate: ~4 KB (embedding) + ~0.5 KB (text fields) ≈ 4.5 KB,
well within DynamoDB's 400 KB per-item limit.

## 4. API Contracts

### `POST /ingest`
Stores an email + its embedding. Useful for pre-seeding the corpus.

**Request**
```json
{
  "subject":     "Q3 planning",
  "senderName":  "Alice",
  "senderEmail": "alice@example.com",
  "bodyText":    "Let's schedule the Q3 kickoff…"
}
```
**Response 200**
```json
{ "success": true, "id": "a1b2c3d4-..." }
```

### `POST /reply`
Embeds the email, retrieves similar past emails, generates a reply, and stores
the email as a side effect (builds the corpus automatically as you use it).

**Request**
```json
{
  "subject":       "Follow-up on proposal",
  "senderName":    "Carol",
  "senderEmail":   "carol@example.com",
  "bodyText":      "Just wanted to check in on the proposal status.",
  "threadHistory": [],
  "tone":          "professional"
}
```
**Response 200**
```json
{
  "replyText":      "Hi Carol, thank you for following up…",
  "modelUsed":      "anthropic.claude-3-haiku-20240307-v1:0",
  "retrievedCount": 3,
  "truncated":      false
}
```

## 5. Extension Provider System

The extension uses a pluggable provider pattern so the LLM backend can be
swapped without touching the Gmail DOM code.

```
background.js
└── provider-registry.js  ── getProvider(id) ──► one of:
        ├── dummy-provider.js       no API, instant mock reply
        ├── claude-provider.js      direct Anthropic API (browser → Anthropic)
        ├── openai-provider.js      direct OpenAI API   (browser → OpenAI)
        └── aws-backend-provider.js via Lambda          (browser → AWS → Bedrock)
```

Each provider implements the same interface:
```javascript
{
  id:             string,
  name:           string,
  isConfigured(config):              boolean,
  generateReply(request, config):    Promise<{ replyText, providerId, modelUsed, truncated }>,
  getConfigFields():                 ConfigField[],
}
```

Adding a new provider (e.g. Gemini) requires only:
1. Create `llm/gemini-provider.js` implementing the interface above
2. Import and register it in `llm/provider-registry.js`
3. Add a settings section in `options.html` / `options.js`

## 6. AWS Services — Cost Model

| Service              | Idle cost   | Per-use cost                           |
|----------------------|-------------|----------------------------------------|
| DynamoDB (PAY_PER_REQUEST) | $0    | ~$0.000001 per read/write             |
| Lambda               | $0          | ~$0.000002 per 256 MB-sec invocation  |
| API Gateway HTTP API | $0          | ~$0.000001 per request                |
| CloudWatch Logs      | ~$0.001/day | (7-day retention, minimal volume)     |
| Bedrock Titan Embed  | $0 idle     | $0.00002 per 1 000 tokens             |
| Bedrock Claude Haiku | $0 idle     | $0.00025/1K input + $0.00125/1K output|

**Estimated cost for a demo session (50 reply generations):**  
< $0.10 total. Running `terraform destroy` after the demo brings ongoing cost to **$0**.

## 7. Bedrock Model Access Setup

Before `terraform apply`, you must enable the two models in the AWS Console.
This is a one-time click-through agreement per AWS account.

**Step-by-step:**

1. Open the AWS Console and navigate to:  
   **Services → Amazon Bedrock → Model access**  
   (ensure the region selector at the top-right shows `us-east-1`)

2. Click **"Manage model access"** (button in the top-right of the page).

3. In the model list, check the boxes next to:
   - **Amazon → Titan Embeddings V2** (no terms to accept, instant)
   - **Anthropic → Claude 3 Haiku** (requires accepting Anthropic's terms)

4. Click **"Request model access"** at the bottom of the page.

5. Wait 1–5 minutes. Refresh the Model access page until both models show  
   **"Access granted"** in the Status column.

6. Verify from the CLI:
   ```bash
   aws bedrock list-foundation-models --region us-east-1 \
     --query "modelSummaries[?contains(modelId,'titan-embed-text-v2')].[modelId,modelLifecycle]"

   aws bedrock list-foundation-models --region us-east-1 \
     --query "modelSummaries[?contains(modelId,'claude-3-haiku')].[modelId,modelLifecycle]"
   ```
   Both should return results with lifecycle status `ACTIVE`.

## 8. Deploy / Destroy Commands

### First-time setup
```bash
# 1. Install Terraform (if not already installed)
#    https://developer.hashicorp.com/terraform/install
terraform -version   # verify ≥ 1.6

# 2. Deploy everything
cd infrastructure/
terraform init       # download AWS provider
terraform plan       # preview what will be created
terraform apply      # type 'yes' to confirm — takes ~60 seconds

# 3. Copy the printed api_url into the Chrome extension:
#    Extension toolbar → "Open Settings" → AWS Backend (RAG) → paste URL → Save
```

### Redeploy after code changes
```bash
cd infrastructure/
terraform apply      # Terraform detects changed lambda_package.zip and redeploys
```

### Tear down everything (zero cost)
```bash
cd infrastructure/
terraform destroy    # type 'yes' — deletes all AWS resources including DynamoDB data
```

### Useful debug commands
```bash
# Tail Lambda logs in real time
aws logs tail /aws/lambda/gmail-ai-reply-api --follow --region us-east-1

# Scan the DynamoDB table to see stored emails (shows count + ids)
aws dynamodb scan \
  --table-name gmail-ai-reply-emails \
  --select COUNT \
  --region us-east-1

# Test the /reply endpoint directly (no browser needed)
curl -s -X POST https://<your-api-url>/reply \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test",
    "senderName": "Test Sender",
    "senderEmail": "test@example.com",
    "bodyText": "This is a test email.",
    "tone": "brief"
  }' | python3 -m json.tool
```

## 9. Design Decisions & Trade-offs

| Decision | Chosen approach | Alternative | Why |
|---|---|---|---|
| Vector store | DynamoDB + Lambda scan | OpenSearch Serverless, pgvector | Zero idle cost; O(n) scan is fine at academic scale |
| Embeddings | Titan Embeddings V2 (512-dim) | OpenAI text-embedding-3-small | Keeps everything in AWS; no extra API key |
| LLM | Claude 3 Haiku via Bedrock | Direct Anthropic API | Bedrock handles auth via IAM — no per-user API key management |
| API auth | None | Cognito, API key | Academic MVP; add `x-api-key` to API Gateway as first hardening step |
| Lambda packaging | archive_file (pure Python) | Docker container, Lambda Layer | No compiled dependencies needed — stdlib + boto3 (pre-installed) |
| CORS | `allow_origins = ["*"]` | Extension ID allowlist | Extension IDs change per install; wildcard is simplest without auth |

## 10. Upgrade Path (post-academic)

When scaling beyond demo:
1. **Vector DB** → Add OpenSearch Serverless with k-NN index, replace `find_similar()` in `store.py`
2. **Auth** → Add Cognito User Pool + API Gateway JWT authorizer; add `Authorization` header in `aws-backend-provider.js`
3. **Gmail API** → Replace DOM scraping in `content.js` with OAuth + Gmail REST API for reliability
4. **Email ingestion pipeline** → Add an SQS queue + second Lambda to async-process new emails without blocking reply generation
