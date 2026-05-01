# MailManager — Gmail AI Reply with AWS RAG

A Chrome extension that reads your Gmail and generates replies using AI.
What makes it interesting: it gets *smarter over time* by remembering your past emails
and using them as context — that's the RAG part.

```
You open an email → click "✨ Generate AI Reply"
        ↓
AWS Lambda embeds the email (Titan Embeddings)
        ↓
Finds your 3 most similar past emails in DynamoDB
        ↓
Feeds them as context to Claude 3 Haiku (Bedrock)
        ↓
Returns a reply that sounds like you
```

## Repo Structure

```
extension/          Chrome extension (content script, background worker, UI)
backend/            Python Lambda — embed → retrieve → generate
infrastructure/     Terraform — one command to create or destroy all AWS resources
tests/              42 Jest tests, run without any API key
DESIGN.md           Full architecture, RAG pipeline, cost breakdown, upgrade path
```

## Try It Without Any API Key

The extension ships with a **Dummy provider** — instant mock replies, no credentials needed.
Good for verifying the full browser → extension pipeline before touching AWS.

```bash
cd gmail-ai-reply
npm install && npm test          # 42 tests, all green
```

Then load the extension in Chrome: `chrome://extensions` → Developer mode → Load unpacked → select this folder.

## Deploy the AWS Backend

**One-time:** enable two models in [Bedrock Model Access](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess)
(us-east-1): **Titan Embeddings V2** and **Claude 3 Haiku**. Takes about 2 minutes.

```bash
cd infrastructure/
terraform init
terraform apply          # ~60 seconds — prints your API URL when done
```

Paste the `api_url` output into the extension: toolbar icon → Open Settings → AWS Backend (RAG).

**Tear everything down** (cost goes to $0):
```bash
terraform destroy
```

## Cost

Essentially free at demo scale. All AWS resources are serverless with zero idle cost.
A typical session of 50 reply generations costs under $0.10 total.

## Tech

`Chrome Extension (MV3)` · `Python 3.12 Lambda` · `Amazon Bedrock` · `DynamoDB` · `Terraform` · `Jest`

See [DESIGN.md](DESIGN.md) for architecture decisions, the full RAG pipeline diagram, and the upgrade path to production scale.
