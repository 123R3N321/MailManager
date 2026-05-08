# MailManager — Verification Runbook

All commands use the values from the current Terraform deployment. Set the variables block once, then run any section independently.

---

## 0. Variables (set once per session)

You need to configure the basic metadata before running the commands, by configure your ``.env`` then calling:
```bash
source scripts/env.sh
```
from project root dir; alternatiely, feel free to manually configure:

```bash
export API_URL="https://8xw0hh7pdf.execute-api.us-east-1.amazonaws.com"
export REGION="us-east-1"
export ACCOUNT_ID="959762337048"
export TABLE="mailmanager-demo-2546-metadata"
export RAW_BUCKET="mailmanager-demo-2546-raw-mail"
export FRONTEND_BUCKET="mailmanager-frontend-20260508173453055200000004"
export QUEUE_URL="https://sqs.us-east-1.amazonaws.com/${ACCOUNT_ID}/mailmanager-demo-2546-ingest"
export DLQ_URL="https://sqs.us-east-1.amazonaws.com/${ACCOUNT_ID}/mailmanager-demo-2546-ingest-dlq"
export LAMBDA_API="mailmanager-demo-2546-api"
export LAMBDA_WORKER="mailmanager-demo-2546-ingest-worker"
export LAMBDA_SCHED="mailmanager-demo-2546-schedule-stub"
export OS_ENDPOINT="https://search-mailmanager-vectors-ku3xzmar4hhiakqewdr6t3l6du.us-east-1.es.amazonaws.com"
export OS_INDEX="mailmanager-index"
```

---

## 1. Asset Presence Checks

### API Gateway
```bash
aws apigatewayv2 get-apis --region $REGION \
  --query "Items[?contains(Name,'mailmanager')].{Name:Name,Id:ApiId,Endpoint:ApiEndpoint}" \
  --output table
```

### Lambda functions
```bash
aws lambda list-functions --region $REGION \
  --query "Functions[?contains(FunctionName,'mailmanager')].{Name:FunctionName,Runtime:Runtime,State:State}" \
  --output table
```

### DynamoDB table
```bash
aws dynamodb describe-table --region $REGION --table-name $TABLE \
  --query "Table.{Name:TableName,Status:TableStatus,Items:ItemCount,BillingMode:BillingModeSummary.BillingMode}" \
  --output table
```

### S3 buckets
```bash
aws s3 ls s3://$RAW_BUCKET --region $REGION --summarize 2>&1 | tail -3
aws s3 ls s3://$FRONTEND_BUCKET --region $REGION --summarize 2>&1 | tail -3
```

### SQS queues (ingest + DLQ)
```bash
aws sqs get-queue-attributes --region $REGION --queue-url $QUEUE_URL \
  --attribute-names All \
  --query "Attributes.{Visible:ApproximateNumberOfMessages,InFlight:ApproximateNumberOfMessagesNotVisible,DLQ:RedrivePolicy}" \
  --output table

aws sqs get-queue-attributes --region $REGION --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages \
  --query "Attributes" --output table
```

### OpenSearch domain
```bash
aws opensearch describe-domain --region $REGION --domain-name mailmanager-vectors \
  --query "DomainStatus.{Status:ProcessingStatus,Endpoint:Endpoint,EngineVersion:EngineVersion}" \
  --output table 2>/dev/null || \
aws es describe-elasticsearch-domain --region $REGION --domain-name mailmanager-vectors \
  --query "DomainStatus.{Endpoint:Endpoint,EngineVersion:ElasticsearchVersion}" \
  --output table
```

### Secrets Manager
```bash
aws secretsmanager list-secrets --region $REGION \
  --query "SecretList[?contains(Name,'mailmanager')].{Name:Name,LastChanged:LastChangedDate}" \
  --output table
```

### EventBridge rule
```bash
aws events describe-rule --region $REGION \
  --name "mailmanager-demo-2546-sync-schedule" \
  --query "{Name:Name,State:State,Schedule:ScheduleExpression}" \
  --output table
```

### CloudWatch log groups
```bash
aws logs describe-log-groups --region $REGION \
  --log-group-name-prefix "/aws/lambda/mailmanager" \
  --query "logGroups[].{Name:logGroupName,RetentionDays:retentionInDays,SizeMB:storedBytes}" \
  --output table
```

---

## 2. API Endpoint Tests

### Health check
```bash
curl -s $API_URL/health | jq .
# Expected: {"status":"ok","service":"mailmanager-api",...}
```

### Seed demo data (run once after deploy)
```bash
curl -s -X POST $API_URL/ingest/demo | jq .
# Expected: {"status":"ingested","mailboxes":2,"threads":10,"messages":35,...}
```

### List mailboxes
```bash
curl -s "$API_URL/mailboxes" | jq '.mailboxes[] | {id:.mailboxId, provider:.provider, email:.email}'
# Expected: 2 mailboxes — mbx-gmail and mbx-outlook
```

### List threads (Gmail mailbox)
```bash
curl -s "$API_URL/threads?mailboxId=mbx-gmail" | jq '.threads | length, .[0].subject'
# Expected: 5 threads, first subject printed
```

### Get a specific thread
```bash
curl -s "$API_URL/threads/thr-001" | jq '.thread | {subject:.subject, messages:(.messages|length)}'
# Expected: subject + 4 messages
```

### Generate AI reply (Chrome extension endpoint)
```bash
curl -s -X POST $API_URL/reply \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Invoice approval needed",
    "senderName": "Finance Team",
    "senderEmail": "finance@company.com",
    "bodyText": "Hi, please approve invoice INV-2048 for $18,420 by Friday.",
    "threadHistory": [],
    "tone": "professional"
  }' | jq '{model:.model, retrieval:.retrievalMode, reply:.replyText}'
# Expected: model="bedrock", replyText=AI-generated reply
```

### Thread summary
```bash
curl -s -X POST $API_URL/threads/thr-001/summary | jq '{model:.model, short:.summary.short, next:.summary.nextStep}'
# Expected: model="bedrock", AI-generated summary
```

### Draft reply for a thread
```bash
curl -s -X POST $API_URL/threads/thr-001/draft-reply \
  -H "Content-Type: application/json" \
  -d '{"intent":"confirm invoice approval and next steps"}' \
  | jq '{model:.model, draft:.draft}'
# Expected: model="bedrock", draft=AI-written reply
```

### Action items extraction
```bash
curl -s -X POST $API_URL/threads/thr-001/action-items | jq '.actionItems[] | {task:.task, due:.dueDate, priority:.priority}'
# Expected: list of extracted action items with due dates
```

### Semantic search
```bash
curl -s -X POST $API_URL/search \
  -H "Content-Type: application/json" \
  -d '{"query":"invoice approval deadline","mailboxId":"mbx-gmail"}' \
  | jq '{model:.model, retrieval:.retrievalMode, answer:.answer, sources:(.sources|length)}'
# Expected: answer grounded in email content, sources list
```

### Enqueue a message to the ingest worker
```bash
curl -s -X POST $API_URL/enqueue \
  -H "Content-Type: application/json" \
  -d '{"source":"manual-test","ts":"'"$(date -u +%s)"'"}' | jq .
# Expected: {"status":"enqueued",...}
```

---

## 3. Log Tailing — Real-Time Activity

### Watch API Lambda live (reflects every button click in the extension)
```bash
aws logs tail /aws/lambda/$LAMBDA_API \
  --region $REGION \
  --follow \
  --format short
```

### Watch API worker live (fires whenever user clicks ai reply plug-in button)
```bash
aws logs tail /aws/lambda/$LAMBDA_API --region $REGION --follow --format short
```

### Watch ingest worker live (fires when SQS messages arrive)
```bash
aws logs tail /aws/lambda/$LAMBDA_WORKER \
  --region $REGION \
  --follow \
  --format short
```

### Watch schedule stub live
```bash
aws logs tail /aws/lambda/$LAMBDA_SCHED \
  --region $REGION \
  --follow \
  --format short
```

### Last 5 minutes of API logs (post-hoc review)
```bash
aws logs tail /aws/lambda/$LAMBDA_API \
  --region $REGION \
  --since 5m \
  --format short
```

### Filter logs for Bedrock calls only
```bash
aws logs filter-log-events \
  --region $REGION \
  --log-group-name /aws/lambda/$LAMBDA_API \
  --start-time $(date -d '30 minutes ago' +%s000 2>/dev/null || date -v-30M +%s000) \
  --filter-pattern "bedrock" \
  --query "events[].message" \
  --output text
```

### Filter logs for errors only
```bash
aws logs filter-log-events \
  --region $REGION \
  --log-group-name /aws/lambda/$LAMBDA_API \
  --start-time $(date -d '1 hour ago' +%s000 2>/dev/null || date -v-1H +%s000) \
  --filter-pattern "ERROR" \
  --query "events[].message" \
  --output text
```

### Filter logs for /reply endpoint activity
```bash
aws logs filter-log-events \
  --region $REGION \
  --log-group-name /aws/lambda/$LAMBDA_API \
  --start-time $(date -d '1 hour ago' +%s000 2>/dev/null || date -v-1H +%s000) \
  --filter-pattern '"/reply"' \
  --query "events[].message" \
  --output text
```

---

## 4. Ingest Worker — Trigger and Verify

### Send demo data through the vectorization pipeline
```bash
aws sqs send-message \
  --region $REGION \
  --queue-url $QUEUE_URL \
  --message-body "{\"bucket\":\"${RAW_BUCKET}\",\"key\":\"demo/demo_emails.json\"}"
```

### Poll queue depth until empty (worker consumed the message)
```bash
watch -n 2 'aws sqs get-queue-attributes --region '$REGION' \
  --queue-url '$QUEUE_URL' \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
  --query Attributes --output table'
```

### Check DLQ for failed messages
```bash
aws sqs get-queue-attributes --region $REGION --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages \
  --query "Attributes.ApproximateNumberOfMessages" --output text
# Expected: 0 (no failures)
```

---

## 5. OpenSearch Index Checks

### Create the vector index (run once after deploy)
```bash
curl -s -X PUT "${OS_ENDPOINT}/${OS_INDEX}" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": { "index": { "knn": true } },
    "mappings": {
      "properties": {
        "email_vector": { "type": "knn_vector", "dimension": 1536 },
        "threadId":  { "type": "keyword" },
        "messageId": { "type": "keyword" },
        "mailboxId": { "type": "keyword" },
        "subject":   { "type": "text" },
        "sender":    { "type": "keyword" },
        "sentAt":    { "type": "date" },
        "snippet":   { "type": "text" },
        "body":      { "type": "text" }
      }
    }
  }' | jq .
# Expected: {"acknowledged":true,"index":"mailmanager-index"}
```

### Check index document count
```bash
curl -s "${OS_ENDPOINT}/${OS_INDEX}/_count" | jq .
# Expected: {"count":35,...} after ingest worker runs
```

### Run a test vector search directly against OpenSearch
```bash
curl -s -X POST "${OS_ENDPOINT}/${OS_INDEX}/_search" \
  -H "Content-Type: application/json" \
  -d '{"size":3,"query":{"match":{"subject":"invoice"}}}' \
  | jq '.hits.hits[] | {subject:._source.subject, score:._score}'
```

---

## 6. DynamoDB Content Checks

### Count items by entity type
```bash
aws dynamodb scan --region $REGION --table-name $TABLE \
  --filter-expression "entityType = :t" \
  --expression-attribute-values '{":t":{"S":"MailboxConnection"}}' \
  --select COUNT --query Count --output text
# Expected: 2

aws dynamodb scan --region $REGION --table-name $TABLE \
  --filter-expression "entityType = :t" \
  --expression-attribute-values '{":t":{"S":"EmailThread"}}' \
  --select COUNT --query Count --output text
# Expected: 10

aws dynamodb scan --region $REGION --table-name $TABLE \
  --filter-expression "entityType = :t" \
  --expression-attribute-values '{":t":{"S":"EmailMessage"}}' \
  --select COUNT --query Count --output text
# Expected: 35
```

### Check S3 for ingested demo data
```bash
aws s3 ls s3://$RAW_BUCKET/demo/ --region $REGION
# Expected: demo_emails.json present after /ingest/demo call

aws s3 ls s3://$RAW_BUCKET/_healthcheck/ --region $REGION
# Expected: last.json present after /health call
```
