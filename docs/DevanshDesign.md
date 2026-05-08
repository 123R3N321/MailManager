**Email RAG SaaS Platform**

*Cloud Computing Final Project Design Document*

| Project Type | AI-powered multi-tenant SaaS for email summarization, reply drafting, action-item extraction, and semantic inbox search. |
| :---- | :---- |
| **Primary Cloud Pattern** | Event-driven serverless microservices with retrieval-augmented generation (RAG). |
| **Target Users** | Professionals and teams managing multiple Gmail / Outlook inboxes with high email volume. |

Prepared for: Cloud Computing Final Project  
Members: Devansh Vikram, Brandon Khong

# 	

# **1\. Executive Summary**

Email RAG SaaS Platform is a secure, cloud-native software-as-a-service product that helps users manage large volumes of email faster and more accurately. The system connects to multiple email providers such as Gmail and Outlook, ingests messages and threads, creates embeddings for semantic retrieval, and uses large language models to generate concise summaries, draft replies, and extract action items. The platform is designed as a multi-tenant application, so each customer can manage one or more linked mailboxes while staying isolated from other tenants.

The proposed AWS architecture favors managed services to reduce operational overhead, improve elasticity, and fit the workload profile of bursty inbound events and asynchronous AI processing. Core patterns include serverless APIs, event queues, workflow orchestration, object storage, metadata indexing, vector search, and observability pipelines.

| Design assumption: this document describes a production-ready target architecture, not just a classroom prototype. Where multiple valid AWS choices exist, the document selects one primary option and briefly notes alternatives. |
| :---- |

# **2\. Problem Statement**

Professionals lose significant time to repetitive email work: reading long threads, finding the actual decision buried inside a conversation, identifying tasks, and replying consistently. The pain becomes worse when users manage multiple mailboxes or shared support/recruiting/operations inboxes.

* Manual processing is slow and expensive.  
* Important tasks are missed because action items are not extracted consistently.  
* Traditional keyword search fails when the user remembers the meaning of an email but not the exact words.  
* Switching between Gmail, Outlook, and multiple accounts creates workflow fragmentation.  
* Sensitive business communication requires strong security, auditing, and tenant isolation.

# 

# **3\. Product Goals and Non-Goals**

| Category | Items |
| :---- | :---- |
| Goals | Fast thread summarization, smart reply drafting, action-item extraction, semantic inbox search, multi-account linking, secure multi-tenancy, scalable SaaS operations. |
| Non-Goals | Building a full email provider, replacing Gmail/Outlook UI entirely, autonomous sending without user approval, and training proprietary foundation models from scratch. |
| Success Metrics | Time-to-summary, draft acceptance rate, search relevance, API latency, queue backlog health, uptime, and tenant retention. |

# **4\. Functional Requirements**

* Users can sign up, sign in, and belong to an organization/tenant.  
* Users can connect one or more email accounts, such as Gmail and Outlook, via OAuth-based provider linking.  
* The platform can ingest messages, thread structure, participants, attachments metadata, and provider labels/folders.  
* The system can generate thread summaries, draft suggested replies, and extract action items from selected emails or conversations.  
* Users can ask natural-language questions over their inbox and receive answers grounded in retrieved emails.  
* Users can switch between linked inboxes without logging out and without mixing tenant data.  
* Admins can view usage, billing, audit records, provider sync health, and security events.

# **5\. Non-Functional Requirements**

| Attribute | Target |
| :---- | :---- |
| Scalability | Support bursty ingestion and asynchronous AI jobs without manual server scaling. |
| Availability | Highly available public API and durable job execution with retries and dead-letter handling. |
| Security | OAuth provider linking, encryption at rest and in transit, least-privilege IAM, audit logs, and tenant isolation. |
| Performance | Interactive API calls under low seconds for metadata; AI-heavy tasks handled asynchronously with progress states. |
| Observability | Centralized logs, business metrics, traces, alarms, and dashboards. |
| Extensibility | Easy addition of new providers, new LLM prompts, and new extraction pipelines. |

# **6\. High-Level Architecture Explanation** 

Think of the architecture as seven layers arranged left to right.

* Layer 1 – Client layer: a React/Next.js web app served through Amazon CloudFront. The browser talks only to the public API layer and to the authentication provider.  
* Layer 2 – Edge and security layer: Route 53 points the product domain to CloudFront and the API domain to API Gateway. AWS WAF protects both the web app and API from common web attacks, bad bots, and abusive request patterns.  
* Layer 3 – Identity layer: Amazon Cognito handles user sign-up, sign-in, session tokens, organization membership claims, and federation. External provider OAuth consent is used for Gmail and Microsoft 365 mailbox access.  
* Layer 4 – Application/API layer: Amazon API Gateway fronts Lambda-based microservices. These services implement mailbox management, search, summaries, reply generation requests, admin operations, and webhook/event endpoints.  
* Layer 5 – Workflow and event layer: Amazon EventBridge, Amazon SQS, and AWS Step Functions coordinate ingestion, retries, job fan-out, and asynchronous AI processing. This keeps the user-facing API responsive while heavy work happens in the background.  
* Layer 6 – Data and AI layer: raw email payloads and attachments live in Amazon S3; operational metadata lives in Amazon DynamoDB or Amazon Aurora PostgreSQL; embeddings and semantic search indexes live in Amazon OpenSearch Serverless vector collections; LLM inference is handled through Amazon Bedrock.  
* Layer 7 – Operations layer: Amazon CloudWatch, AWS X-Ray/tracing integrations, CloudTrail, and Security Hub provide monitoring, auditing, alerting, and operational visibility.

In the diagram, arrows would show two major flows:

* Synchronous control path: browser \-\> CloudFront \-\> API Gateway \-\> Lambda \-\> metadata database/cache \-\> browser.  
* Asynchronous content intelligence path: email provider webhook or scheduled sync \-\> ingestion Lambda \-\> queue/workflow \-\> storage \+ embedding \+ Bedrock inference \-\> results persisted \-\> browser polls or receives updated job status.

# **7\. Frontend Design**

Recommended stack: Next.js (React) \+ TypeScript hosted on Amazon S3 and delivered via CloudFront, or alternatively deployed via AWS Amplify Hosting. The UI is organized around mailbox selection, thread reading, AI assistant actions, and search.

| Frontend Module | Responsibilities |
| :---- | :---- |
| Authentication UI | Login, registration, MFA prompts, tenant selection, session refresh, and logout. |
| Mailbox Switcher | Displays linked Gmail/Outlook accounts and the current active mailbox context. |
| Thread Workspace | Shows thread list, full thread view, summary card, suggested replies, action items, and source citations to retrieved emails. |
| Search Experience | Natural-language search bar, retrieved email snippets, filters by provider/folder/date/sender. |
| Admin Console | Tenant configuration, provider connection status, usage analytics, audit logs, and billing summary. |

# **8\. Authentication and Authorization**

Authentication must cover two distinct trust domains: product login and mailbox-provider access.

* Product identity: Amazon Cognito User Pools manage application users, passwords, or social sign-in, hosted UI, MFA, and JWT issuance.  
* Provider linking: each user grants Gmail or Outlook access through OAuth 2.0 consent. Provider refresh tokens are stored securely, encrypted, and scoped as narrowly as possible.  
* Authorization model: every request carries tenant\_id, user\_id, and role claims. Backend services enforce row-level and document-level access checks before any email content is returned.  
* Service-to-service authorization: Lambda roles use IAM least privilege. No service receives blanket access to all data stores unless strictly required.  
* Optional enterprise extension: support SAML/OIDC federation for organization-wide SSO.

| Access Level | Example Permissions |
| :---- | :---- |
| End User | Read linked mailbox metadata, request summaries, ask inbox questions, and generate draft replies. |
| Org Admin | Manage users, view audit logs, manage provider policies, and view usage and billing. |
| System Worker | Read queue messages, fetch encrypted provider tokens, read/write embeddings, and job results. |
| Security Auditor | Read compliance logs and incident dashboards without content mutation rights. |

# **9\. Core AWS Services Used**

| AWS Service | Purpose in This System |
| :---- | :---- |
| Amazon CloudFront | Global CDN for frontend delivery, TLS termination, caching, and edge protection integration. |
| Amazon S3 | Stores frontend static assets, raw email payload archives, attachment objects, export files, and prompt/result snapshots where needed. |
| Amazon Route 53 | DNS routing for product and API domains. |
| Amazon Cognito | User authentication, JWT tokens, hosted login, and federation support. |
| Amazon API Gateway | Public HTTPS API for browser/mobile clients and webhook endpoints. |
| AWS Lambda | Serverless compute for API handlers, ingestion workers, embedding jobs, and post-processing. |
| Amazon EventBridge | Schedules sync jobs and routes domain events across services. |
| Amazon SQS | Buffer ingestion and AI jobs to smooth load and support retries. |
| AWS Step Functions | Coordinates multi-step workflows such as ingest \-\> chunk \-\> embed \-\> summarize \-\> persist. |
| Amazon DynamoDB | Fast metadata store for tenants, mailbox mappings, jobs, and lightweight email/thread indexes. |
| Amazon Aurora PostgreSQL | Relational store for billing, organizations, RBAC, reporting, and transactional application data if stronger SQL requirements exist. |
| Amazon OpenSearch Serverless | Vector \+ keyword search layer for semantic retrieval over email content. |
| Amazon Bedrock | Managed LLM and embedded access for summarization, smart reply, Q\&A, and extraction. |
| Amazon SES | Sends product notifications, such as onboarding, alerts, and optional outbound draft delivery workflows. |
| AWS KMS | Encryption key management for tokens, secrets, S3 objects, and database encryption. |
| AWS Secrets Manager | Stores OAuth client secrets, webhook signing secrets, and other credentials. |
| Amazon CloudWatch | Metrics, logs, dashboards, alarms, and operational analytics. |
| AWS WAF | Protects CloudFront and API Gateway from malicious traffic. |
| AWS CloudTrail | Audits AWS API activity for governance and incident response. |

# **10\. Database and Storage Design**

The platform uses polyglot persistence because email intelligence workloads mix transactional metadata, large unstructured content, and vector similarity search.

| Store | Data Examples | Why It Fits |
| :---- | :---- | :---- |
| Amazon DynamoDB | Tenant profile, linked mailbox records, sync cursors, job status, thread summary metadata, action-item records. | Low-latency key-value access, autoscaling, and easy partitioning by tenant and mailbox. |
| Amazon Aurora PostgreSQL | Users, organizations, subscriptions, invoices, role mappings, feature flags, analytics rollups. | Strong relational integrity and rich SQL for admin/reporting workloads. |
| Amazon S3 | Raw MIME payloads, normalized JSON email bodies, attachments, exported reports, prompt/response archives. | Durable object storage for large blobs and lifecycle policies. |
| Amazon OpenSearch Serverless (Vector) | Embeddings for email chunks, thread-level vectors, and hybrid search indexes. | Supports semantic retrieval plus filterable search over metadata. |
| Optional ElastiCache Redis | Session acceleration, short-term caching of hot thread summaries, and rate-limit counters. | Reduces repeated reads and improves user-perceived latency. |

Recommended partitioning rules:

* Prefix every primary record with tenant\_id so tenant isolation is explicit in data access patterns.  
* Keep raw email content in S3 and store only references plus selected searchable fields in DynamoDB/OpenSearch.  
* Use separate encryption contexts or per-tenant key strategies for highly sensitive enterprise deployments.  
* Define retention policies for deleted accounts, revoked mailbox connections, and expired AI job artifacts.

# **11\. Data Model (Logical)**

| Entity | Important Fields |
| :---- | :---- |
| Tenant | tenant\_id, name, plan, region, security\_policy, created\_at |
| User | user\_id, tenant\_id, cognito\_sub, email, role, status, last\_login\_at |
| MailboxConnection | mailbox\_id, tenant\_id, provider, provider\_account\_id, encrypted\_refresh\_token\_ref, sync\_state, scopes |
| EmailThread | thread\_id, tenant\_id, mailbox\_id, subject, participants, latest\_message\_at, labels, search\_doc\_ref |
| EmailMessage | message\_id, thread\_id, sender, recipients, timestamp, snippet, s3\_object\_key, attachment\_refs |
| AIJob | job\_id, tenant\_id, type, status, input\_ref, output\_ref, model\_id, started\_at, completed\_at, error\_code |
| Summary | summary\_id, thread\_id, style, summary\_text, citations, model\_id, freshness\_ts |
| ActionItem | action\_id, thread\_id, owner\_guess, due\_date\_guess, confidence, source\_message\_id, status |
| DraftReply | draft\_id, thread\_id, tone, generated\_text, user\_edits, approval\_status |
| AuditEvent | event\_id, actor\_id, tenant\_id, action, resource\_type, resource\_id, timestamp, ip\_address |

# **12\. API Design and Endpoints**

All endpoints are versioned under /v1. Authentication uses bearer JWTs except for internal webhooks that use signed secrets or provider-specific verification.

| Method | Endpoint | Purpose |
| :---- | :---- | :---- |
| POST | /v1/auth/login | Log in through Cognito or hosted auth flow token exchange. |
| POST | /v1/auth/logout | Invalidate the session on the client side and revoke refresh tokens where applicable. |
| GET | /v1/me | Return the current user profile, tenant, roles, and linked mailboxes. |
| POST | /v1/mailboxes/link | Start Gmail/Outlook OAuth linking flow. |
| GET | /v1/mailboxes | List linked mailboxes for the current tenant/user. |
| POST | /v1/mailboxes/{mailboxId}/sync | Trigger incremental sync for a mailbox. |
| GET | /v1/threads | List email threads with filters and pagination. |
| GET | /v1/threads/{threadId} | Return thread details and message metadata. |
| POST | /v1/threads/{threadId}/summaries | Create a summary job for a thread. |
| POST | /v1/threads/{threadId}/draft-replies | Create a suggested reply draft. |
| POST | /v1/threads/{threadId}/action-items | Extract or refresh action items. |
| POST | /v1/search | Natural-language semantic inbox query across the selected mailbox scope. |
| GET | /v1/jobs/{jobId} | Check asynchronous job status and fetch result references. |
| POST | /v1/webhooks/gmail | Receive Gmail push/webhook events. |
| POST | /v1/webhooks/outlook | Receive Microsoft Graph notifications. |
| GET | /v1/admin/usage | Return usage, quotas, billing, and system health summary. |
| GET | /v1/admin/audit | Return tenant audit logs with filters. |

Example endpoint behavior: POST /v1/search

* Input: query, mailbox\_scope, provider filters, date range, top\_k.  
* Backend: generate query embedding, run hybrid vector \+ keyword retrieval in OpenSearch, fetch top source chunks, call Bedrock with retrieved context, return answer plus citations to original emails.  
* Output: grounded answer, cited emails, relevance metadata, and optionally follow-up suggestions.

# **13\. End-to-End Workflow**

## **13.1 User Registration and Login**

* User opens the web app via CloudFront.  
* Frontend redirects to Cognito-hosted sign-in or embedded auth flow.  
* After authentication, Cognito returns JWTs to the frontend.  
* Frontend stores tokens securely and calls /v1/me to load tenant and mailbox context.

## **13.2 Mailbox Linking Workflow**

* User clicks “Link Gmail” or “Link Outlook”.  
* Backend returns an OAuth authorization URL with scopes required for read access, metadata, and optional send-as-draft capabilities.  
* Provider consent screen is completed.  
* Callback endpoint exchanges code for tokens, encrypts the refresh token using KMS-backed secret handling, and stores the connection record.  
* A mailbox bootstrap sync job is emitted to EventBridge or SQS.

## **13.3 Email Ingestion and Indexing Workflow**

* A provider webhook event or scheduled sync indicates new or updated email content.  
* API Gateway or EventBridge triggers ingestion Lambda.  
* Ingestion Lambda fetches changed messages from the provider API and writes raw payloads to S3.  
* A normalization step extracts subject, participants, cleaned body text, thread relations, provider labels, timestamps, and attachment metadata.  
* Metadata is written to DynamoDB/Aurora.  
* The email body is chunked into retrieval-sized segments.  
* Embeddings are generated through Bedrock embedding models and indexed in OpenSearch Serverless.  
* A completion event updates the sync cursor and marks the mailbox searchable.

## **13.4 Summary Generation Workflow**

* User requests a summary for a thread.  
* API Gateway creates an AIJob record and returns the job\_id immediately.  
* Step Functions orchestrates context gathering, prompt assembly, Bedrock model call, moderation/validation, and result persistence.  
* Summary output is stored with citations to source messages.  
* Frontend polls /v1/jobs/{jobId} or subscribes to notifications, then renders the final summary.

## **13.5 Semantic Search / Inbox Q\&A Workflow**

* User asks a question such as “What did the recruiter say about my start date?”  
* Backend creates an embedding for the user query and runs hybrid retrieval using vector similarity plus metadata filters.  
* Top email chunks and thread metadata are passed to Bedrock as grounding context.  
* Model returns an answer plus supporting citations.  
* System stores the interaction for analytics and prompt-quality improvements.

## **13.6 Smart Reply Workflow**

* User opens a thread and requests a draft.  
* System retrieves the latest thread context, user preferences, and optional tone/style templates.  
* Bedrock generates one or more reply options.  
* The user edits and approves a draft before any provider send/create-draft API is called.  
* Audit event is recorded to preserve traceability.

# **14\. RAG Design Details**

| Stage | Design Choice |
| :---- | :---- |
| Document unit | Chunk at the message body or thread sub-section level to preserve context without making retrieval too coarse. |
| Embedding source | Use a Bedrock-supported embedding model for chunks and queries. |
| Indexing | Store vector embedding \+ metadata filters such as tenant\_id, mailbox\_id, provider, participants, date, labels. |
| Retrieval strategy | Hybrid search: vector similarity \+ lexical keyword matching \+ metadata filters. |
| Grounding | Send top-k retrieved snippets to the LLM with explicit citation instructions. |
| Post-processing | Return summary/answer text, supporting message IDs, confidence indicators, and fallback notices when evidence is weak. |
| Guardrails | Redact secrets where required, limit max context, and reject cross-tenant retrieval paths. |

# **15\. Monitoring, Logging, and Reliability**

* CloudWatch Logs for every Lambda, API Gateway access log, Step Functions execution log, and custom application logs.  
* CloudWatch metrics for request counts, p95 latency, LLM invocation duration, queue depth, failed syncs, OpenSearch query latency, and per-tenant usage.  
* CloudWatch alarms for error-rate spikes, DLQ growth, webhook failures, token refresh failures, Bedrock throttling, and abnormal cost patterns.  
* Distributed tracing across API Gateway, Lambda, and downstream calls to identify slow paths.  
* Dead-letter queues for ingestion and AI jobs that exceed retry policies.  
* Idempotency keys so duplicated provider events do not duplicate indexing or AI jobs.

| Critical Alarm | Trigger Example | Response |
| :---- | :---- | :---- |
| API error rate | 5xx rate exceeds threshold for 5 minutes | Page on-call, inspect recent deploys, and rollback if needed. |
| Queue backlog | SQS visible messages exceed the steady-state band | Scale concurrency, inspect the downstream bottleneck. |
| Sync failures | Mailbox sync error count spikes for a provider | Open provider incident, pause noncritical syncs, notify admins. |
| Search degradation | OpenSearch p95 latency exceeds threshold | Throttle heavy background jobs, inspect index health. |
| Cost anomaly | Daily Bedrock token spend exceeds forecast | Apply usage caps, inspect runaway prompts, or abuse. |

# **16\. Security and Compliance Considerations**

* Encrypt S3, DynamoDB, Aurora, OpenSearch, and Secrets Manager data with KMS-managed keys.  
* Use TLS everywhere and private networking for backend service-to-service traffic where practical.  
* Store provider refresh tokens only in encrypted form and rotate client secrets on schedule.  
* Apply IAM least privilege to every Lambda execution role and data-store policy.  
* Use WAF rules, throttling, and request validation to reduce abuse and prompt-injection entry points.  
* Keep a complete audit trail for login, mailbox linking, draft generation, admin actions, and content export.  
* Implement data retention, deletion, and export workflows to support privacy requirements and enterprise trust.  
* Segregate tenants logically in every persistence layer; for strict enterprise needs, support dedicated environments or per-tenant encryption boundaries.

# **17\. Scalability Strategy**

| Subsystem | Scaling Approach |
| :---- | :---- |
| Frontend | CloudFront edge caching and static asset hosting remove origin pressure. |
| API Layer | Lambda concurrency scales with traffic; API Gateway handles bursty front-door load. |
| Ingestion | SQS buffers spikes from provider webhook bursts and scheduled sync waves. |
| AI Jobs | Asynchronous workers and Step Functions decouple expensive model calls from user request paths. |
| Search | OpenSearch Serverless scales indexing and retrieval separately from transactional systems. |
| Storage | S3 scales virtually without operational planning; DynamoDB partition strategy absorbs tenant growth. |

# **18\. Deployment and DevOps**

Recommended infrastructure-as-code approach: AWS CDK or Terraform. The application should have separate dev, staging, and production environments with CI/CD pipelines for frontend, backend, and infrastructure changes.

* Source control in GitHub or CodeCommit.  
* CI pipeline runs unit tests, linting, security scans, and infrastructure validation.  
* CD pipeline deploys frontend artifacts, Lambda packages/containers, Step Functions definitions, and API Gateway configuration.  
* Use blue/green or canary strategies for risky API changes.  
* Capture environment-specific configs in Parameter Store / Secrets Manager rather than hardcoding values.

# **19\. Cost-Aware Design Notes**

* Use serverless services for variable workloads so idle cost stays low.  
* Cache popular summaries and search results where safe to reduce repeated model calls.  
* Run first-pass triage models or smaller prompts before expensive generation, where possible.  
* Apply S3 lifecycle rules and delete stale raw payloads or prompt traces based on policy.  
* Use asynchronous batching for embeddings rather than tiny per-message requests when feasible.

# **20\. Future Enhancements**

* Team/shared inbox collaboration with assignees and SLA workflows.  
* Fine-grained knowledge graph over people, commitments, deadlines, and organizations across email.  
* Calendar integration for meeting extraction and suggested scheduling actions.  
* Cross-channel intelligence that combines email with Slack, docs, and CRM systems.  
* Per-tenant custom prompts, guardrails, and model routing policies.

# 

# **21\. Risks and Mitigations**

| Risk | Why It Matters | Mitigation |
| :---- | :---- | :---- |
| OAuth token expiry/revocation | Mailbox access can silently break. | Background health checks, token refresh monitoring, reconnect UX, and alerting. |
| Hallucinated replies or summaries | Incorrect output damages trust. | Grounded retrieval, citations, human approval before send, confidence warnings. |
| Cross-tenant leakage | Critical SaaS security failure. | Strict tenant filters, IAM boundaries, automated tests, encryption, and audit logging. |
| Provider API limits | Sync throughput may drop. | Backoff, queueing, provider-specific rate limit policies, incremental cursors. |
| Cost spikes from LLM usage | Can make SaaS unprofitable. | Budget alarms, token caps, caching, model routing, async quotas. |

# **22\. Conclusion**

This project is a strong fit for cloud-native design because email intelligence mixes web traffic, event processing, document storage, vector search, and AI inference. AWS managed services make the system easier to scale, secure, and observe while keeping the architecture modular enough for future provider integrations and enterprise features. The resulting platform is not just an email summarizer; it is a production-style SaaS architecture for intelligent communication workflows.

# **23\. AWS Reference Notes**

The service selections and behavior described above align with official AWS documentation for Cognito, API Gateway, OpenSearch vector search, Bedrock knowledge bases/model usage, Step Functions, CloudWatch, SES, and WAF. Suggested references for the final report bibliography are listed below:

* Amazon Cognito User Pools Developer Guide.  
* Amazon API Gateway Developer Guide: HTTP APIs, REST APIs, and endpoint types.  
* Amazon OpenSearch Service Developer Guide: vector search, k-NN, and serverless vector collections.  
* Amazon Bedrock Documentation and Knowledge Bases User Guide.  
* AWS Step Functions Developer Guide.  
* Amazon CloudWatch User Guide.  
* Amazon SES Developer Guide.  
* AWS WAF Developer Guide.