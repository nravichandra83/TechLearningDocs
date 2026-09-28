You don't always need a separate embedding service in a RAG pipeline. It is an architectural choice, not a mandatory component.

For your production RAG system, the key question is: Should embedding generation be part of the ingestion worker, or should it be an independently deployable service?

## 1. What does an embedding service do?

An embedding service converts text into a numerical vector using an embedding model.

For example:

```
"Employees are eligible for 20 days of leave"
                     │
                     ▼
              Embedding Model
                     │
                     ▼
       [0.12, -0.34, 0.87, ...]
                     │
                     ▼
                Vector DB
```

The same model is used to embed the user's query at retrieval time, so the query and document vectors can be compared.

## 2. Three deployment options

Option 1 · Simple

## Embedding inside the ingestion worker

```
Queue → Worker → Embedding API → Vector DB
```

The worker calls an embedding model directly, such as Azure OpenAI.

Advantages

* Simple architecture

* Fewer services to deploy and monitor

* No additional network hop

* Good for small and medium workloads

Trade-off: Embedding capacity scales with the worker pool, and model integration is coupled to the worker.

Option 2 · Independently scalable

## Separate embedding service

```
Queue → Ingestion Worker
              │
              ▼
       Embedding Service
              │
              ▼
           Vector DB
```

The service exposes an API for generating embeddings.

Advantages

* Independent scaling and deployment

* Centralized batching, throttling and retries

* Reusable by ingestion, query and other applications

* Easier to standardize model versions

Trade-off: Additional operational complexity, network latency and another dependency to manage.

Option 3 · Managed model endpoint

## Use an embedding provider directly

```
Ingestion Worker ──┐
                   ├──► Azure OpenAI
Query Service ─────┘
```

Both services call a managed embedding endpoint directly.

Advantages

* No embedding infrastructure to operate

* Independent scaling of ingestion and query services

* Managed model hosting

Trade-off: Each caller must handle common concerns such as rate limits, retries and model configuration—or use a shared client library.

## 3. Why separate embedding from ingestion?

Consider your enterprise RAG platform ingesting documents for multiple departments.

Suppose you receive 100,000 documents in a short period.

Your ingestion worker performs:

1. Download document.

2. Extract text.

3. Split into chunks.

4. Generate embeddings.

5. Store chunks in the vector DB.

Embedding generation can become a bottleneck because it involves model inference, API quotas and potentially large volumes of text.

If embedding is a separate service, you can scale it independently.

For example:

|Component|Instances|
| --- | --- |
|Ingestion workers|5|
|Embedding workers/service replicas|15|
|Query API|8|

These are illustrative numbers, not sizing recommendations.

However, if you use a managed embedding API, adding 15 service replicas does not automatically increase the provider's throughput quota. You must also account for that quota.

## 4. Do we need the same embedding service for queries?

This is an important distinction.

Both ingestion and query processing need embeddings:

```
INGESTION
Document → Chunks → Embeddings → Vector DB

QUERY
User question → Query embedding → Vector search
```

You should use a compatible embedding model and the same embedding configuration for both sides of a given index.

But the ingestion and query paths do not necessarily need to call the same deployed service.

For example:

```
                  Embedding Model
                   (same version)
                   /            \
                  /              \
       Ingestion Worker       Query API
               │                  │
               ▼                  ▼
          Document vectors    Query vector
               │                  │
               └──────┐   ┌───────┘
                      ▼   ▼
                    Vector DB
```

You could expose one shared embedding endpoint, or have both call the same managed model deployment.

The critical requirement is compatibility, not sharing a particular microservice.

## 5. What I would choose for your RAG implementation

Given that you're building a RAG pipeline with document ingestion, chunking, ChromaDB and evaluation, I would start with this:

```
                  INGESTION
                     │
                     ▼
              Ingestion Worker
                     │
               Extract + Chunk
                     │
                     ▼
          Embedding Client/Module
                     │
             Managed Embedding API
                     │
                     ▼
                  ChromaDB


                    QUERY
                     │
                     ▼
                Query Service
                     │
              Embedding Client
                     │
             Same Embedding Model
                     │
                     ▼
                  ChromaDB
```

Initially, implement the embedding integration as a reusable module or client library, rather than deploying another microservice.

Keep it responsible for:

* Calling the embedding model.

* Batching chunks where supported.

* Handling rate limits and transient failures.

* Applying timeouts and retry policies.

* Tracking token usage and embedding costs.

* Enforcing the configured model version.

When throughput, reuse or operational requirements justify it, you can extract that module into an independently deployed embedding service.

### Interview-ready answer

> "A separate embedding service is not mandatory. For a basic RAG system, I would generate embeddings directly from the ingestion worker using a reusable embedding client. As ingestion volume grows, I would consider separating embedding generation so that it can scale independently, centralize batching and rate-limit management, and serve multiple consumers. I would also distinguish the embedding service from the embedding model: the model can be a managed endpoint, so we may not need to host or operate the model ourselves. Regardless of deployment, ingestion and query embedding must use compatible models and configurations for the same vector index."

Principal Engineer takeaway: Start with a modular design; introduce a separate embedding service when independent scaling, shared usage, or centralized model governance provides a measurable benefit.
