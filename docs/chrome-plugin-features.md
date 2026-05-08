# MailManager Chrome Plugin — Features and How It Works

## What the plugin does

The plugin adds a single **"✨ Generate AI Reply"** button to any open email thread in Gmail. Clicking it reads the current thread, retrieves relevant context from past emails, and returns a ready-to-edit AI-drafted reply inside a modal overlay — without leaving Gmail.

---

## Feature overview

| Feature | Detail |
|---------|--------|
| Button injection | Appears automatically whenever Gmail displays an open thread |
| Thread-aware replies | Reads every message in the thread, not just the latest one |
| RAG enrichment | Retrieves semantically similar past emails from the inbox to ground the reply |
| Multiple AI providers | Dummy (testing), Claude direct API, OpenAI, AWS Backend (Bedrock + RAG) |
| Tone control | Professional, Casual, or Brief — set once in options |
| Language control | Replies in any BCP-47 language code (en, fr, es, zh, etc.) |
| Editable modal | Reply renders in a textarea; edit before copying |
| Copy to clipboard | One-click copy, no manual selection needed |
| Popup status badge | Shows active provider and Ready / Not configured at a glance |

---

## How it works end-to-end

### Step 1 — Gmail DOM monitoring (`content.js`)

A `MutationObserver` watches `document.body` for DOM changes. Every time Gmail navigates to a thread (Gmail is a SPA — it never does a full page reload), the observer fires, detects the presence of `div[data-message-id]` elements, and injects the button.

When injecting, it immediately reads the full thread from the DOM:

```
subject       ← <h2 data-legacy-thread-id> or <h2>
senderName    ← <span email> on the latest message
senderEmail   ← email attribute on the same span
bodyText      ← .a3s class (Gmail's stable body container) on the latest message
threadHistory ← .a3s from every earlier message, oldest first
```

This extracted context is cached in memory. No network call happens at this point.

### Step 2 — Message dispatch (`content.js` → `background.js`)

When the button is clicked, `content.js` sends a `GENERATE_REPLY` message through the Chrome runtime to the background service worker, passing the cached context object:

```js
chrome.runtime.sendMessage({
  type: "GENERATE_REPLY",
  payload: { subject, senderName, senderEmail, bodyText, threadHistory }
})
```

### Step 3 — Provider routing (`background.js`)

The service worker reads the active provider and its config from `chrome.storage.sync`, looks up the provider in the registry, checks it is configured, and calls `provider.generateReply(request, config)`.

### Step 4 — Reply generation (provider-dependent)

#### Claude direct (`claude-provider.js`)
Calls `https://api.anthropic.com/v1/messages` directly from the service worker. The prompt includes the full thread history and tone instruction. No past-email context — only the current thread.

#### AWS Backend / RAG (`aws-backend-provider.js`)
Posts to `https://<api-gateway-id>.execute-api.us-east-1.amazonaws.com/reply`. The Lambda backend does two additional things before generating the reply:

1. **Vector search** — embeds the query (`subject + bodyText`) using Bedrock Titan Embed and runs a k-NN search against OpenSearch to retrieve the 3 most semantically similar emails from the inbox.
2. **RAG prompt** — injects those retrieved emails as grounding context into the prompt alongside the live thread history.

### Step 5 — Modal display (`content.js`)

The reply text is rendered in an overlay modal with an editable textarea and a copy button. The provider/model name is shown in the header so it is always clear which backend generated the reply.

---

## What "context-aware" means in practice

The plugin is context-aware at two levels:

### Level 1 — Thread context (all providers)

Every message in the current thread, not just the last one, is extracted and passed to the model. This means the reply accounts for the full conversation arc: who said what, what was already agreed, and what is still open. A thread with four back-and-forth messages produces a reply that references all four, not just the most recent email.

### Level 2 — Inbox context via RAG (AWS Backend only)

Beyond the current thread, the Lambda retrieves related emails from the broader inbox stored in OpenSearch. For example, if the current email is asking about invoice approval and the inbox contains earlier emails about the same vendor or project, those are surfaced as supporting context. The model is instructed to use only that retrieved evidence when answering, which keeps the reply grounded and reduces hallucination.

The RAG pipeline:

```
User clicks button
       │
       ▼
content.js extracts thread (subject + body + history)
       │
       ▼
background.js sends payload to Lambda /reply
       │
       ▼
Lambda: embed (subject + bodyText) → Bedrock Titan → 1536-dim vector
       │
       ▼
Lambda: k-NN search against OpenSearch index "mailmanager-index"
       │  top-3 semantically similar emails returned
       ▼
Lambda: build prompt
  ┌──────────────────────────────────────────────────────┐
  │  System: You are drafting a reply on behalf of user  │
  │  Thread history: [msg-1] ... [msg-n]                 │
  │  Relevant inbox context: Source 1 … Source 3         │
  │  Email to reply to: From / Subject / Body            │
  │  Instruction: professional / casual / brief          │
  └──────────────────────────────────────────────────────┘
       │
       ▼
Lambda: invoke Bedrock Claude Haiku 4.5
       │
       ▼
Lambda: return { replyText, modelUsed, retrievedCount, retrievalMode }
       │
       ▼
content.js: render reply in modal
```

If OpenSearch is unavailable or the index is empty, the Lambda falls back to a keyword search against DynamoDB and still calls Bedrock. If Bedrock itself fails, it falls back to a template reply. The button never surfaces a blank result.

---

## Where context data is stored

### Live thread context — in-memory only

Extracted by `content.js` on each page navigation and held in a JavaScript variable (`cachedEmailContext`). It is sent to the service worker on button click and discarded. It is never written to disk, storage, or any remote service by the extension itself.

### Inbox email data — AWS (AWS Backend provider only)

| Data | Location | Key / Path |
|------|----------|------------|
| Raw email JSON (all threads + messages) | S3 | `s3://mailmanager-demo-2546-raw-mail/demo/demo_emails.json` |
| Thread metadata + message records | DynamoDB | Table `mailmanager-demo-2546-metadata` — `PK=MAILBOX#<id>`, `SK=THREAD#<id>` |
| Vector embeddings (for k-NN search) | OpenSearch | Index `mailmanager-index` on domain `mailmanager-vectors`, field `email_vector` (1536-dim) |

Inspect the raw data at any time:

```bash
# All email data as stored in S3
aws s3 cp s3://$RAW_BUCKET/demo/demo_emails.json - | jq '.threads[].subject'

# Thread records in DynamoDB
aws dynamodb scan --table-name $TABLE --region $REGION \
  --filter-expression "entityType = :t" \
  --expression-attribute-values '{":t":{"S":"EmailThread"}}' \
  --query "Items[].{subject:{S:subject},mailbox:{S:mailboxId}}" \
  --output table

# Document count in OpenSearch (after ingest worker runs)
curl -s "${OS_ENDPOINT}/${OS_INDEX}/_count" | jq .count
```

### Extension settings — browser storage

Provider choice, API key (Claude/OpenAI), API Gateway URL, tone, and language are stored in `chrome.storage.sync`. This syncs across Chrome profiles signed into the same Google account.

Inspect at any time from the service worker DevTools console (`chrome://extensions` → Service Worker):

```js
chrome.storage.sync.get(null, v => console.log(JSON.stringify(v, null, 2)))
```

---

## Provider comparison

| | Dummy | Claude direct | AWS Backend (RAG) |
|--|-------|---------------|-------------------|
| API key needed | None | Anthropic key in options | None (IAM) |
| Thread history used | No | Yes | Yes |
| Inbox RAG context | No | No | Yes (OpenSearch) |
| Reply quality | Template | Real LLM | Real LLM + grounded |
| Latency | Instant | ~1–2s | ~2–4s |
| API key exposure | N/A | In chrome.storage.sync | Never leaves Lambda |
| Good for | Testing the button flow | Quick real replies | Full demo / class project |

---

## Key source files

| File | Role |
|------|------|
| `content.js` | DOM extraction, button injection, modal rendering |
| `background.js` | Service worker — message routing, provider dispatch |
| `llm/provider-registry.js` | Maps provider IDs to implementations |
| `llm/aws-backend-provider.js` | Calls Lambda `/reply`, returns `{replyText, modelUsed, retrievedCount}` |
| `llm/claude-provider.js` | Direct Anthropic API call, thread-aware prompt |
| `utils/storage.js` | `chrome.storage.sync` read/write, provider config builder |
| `options.html` / `options.js` | Settings UI — provider, keys, tone, language |
| `popup.html` / `popup.js` | Status badge — active provider + configured/not |
| `infra/terraform/lambda/api/handler.py` | Lambda: `/reply` endpoint, RAG pipeline, Bedrock invocation |
