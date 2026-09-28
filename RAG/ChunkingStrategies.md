Yes. **Chunking can be implemented dynamically**, and in a production RAG system I would strongly recommend treating chunking as a configurable strategy rather than hard-coding one splitter.

The key interview point is:

> **Chunking is not just splitting text every N characters. The goal is to create semantically coherent retrieval units while controlling token size, overlap, metadata, and downstream retrieval quality.**

Below are the major strategies, followed by how I would design a **dynamic chunking framework**.

---

# 1. Fixed-size chunking

The simplest approach: split text into chunks of a fixed number of characters or tokens.

### Example

```python
def fixed_size_chunks(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])

        if end >= len(text):
            break

        start = end - overlap

    return chunks


text = """
RAG combines retrieval with generation.
The retrieval component finds relevant documents.
The generation component uses those documents to answer the question.
"""

chunks = fixed_size_chunks(text, chunk_size=50, overlap=10)

for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {chunk}")
```

### Advantages

* Very simple
* Fast
* Predictable chunk size
* Easy to scale

### Problems

You can split sentences or concepts in the middle:

```text
"The retrieval component finds relevant doc"
"uments."
```

This can hurt retrieval quality.

### When to use

Useful as a **baseline** and sometimes for large unstructured text where semantic boundaries are difficult to identify.

---

# 2. Sentence-based chunking

Instead of characters, split on sentence boundaries.

```python
import re

def sentence_chunks(text, sentences_per_chunk=3):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks = []

    for i in range(0, len(sentences), sentences_per_chunk):
        chunk = " ".join(
            sentences[i:i + sentences_per_chunk]
        )
        chunks.append(chunk)

    return chunks


text = """
RAG combines retrieval with generation.
Retrieval finds relevant information.
The information is passed to the LLM.
The LLM generates the final answer.
"""

print(sentence_chunks(text, 2))
```

Output conceptually:

```text
Chunk 1:
RAG combines retrieval with generation.
Retrieval finds relevant information.

Chunk 2:
The information is passed to the LLM.
The LLM generates the final answer.
```

### Advantage

Chunks preserve complete sentences.

### Problem

A sentence isn't necessarily a semantic unit.

For example:

```text
Customer X has a premium subscription.
Their subscription expires in December.
The database is hosted in Azure.
```

Three sentences might belong together—or might not.

---

# 3. Paragraph-based chunking

Use paragraphs as natural boundaries.

```python
def paragraph_chunks(text):
    paragraphs = text.split("\n\n")

    return [
        p.strip()
        for p in paragraphs
        if p.strip()
    ]


text = """
RAG is a retrieval augmented generation architecture.

The retrieval layer searches a vector database.

The LLM uses retrieved information to generate an answer.
"""

chunks = paragraph_chunks(text)

for chunk in chunks:
    print("---")
    print(chunk)
```

This is often better than arbitrary character splitting for documents such as:

* Markdown
* documentation
* technical articles
* knowledge bases

But paragraph sizes can vary dramatically.

You might get:

```text
Chunk 1 = 50 tokens
Chunk 2 = 3000 tokens
Chunk 3 = 100 tokens
```

So in practice paragraph chunking is often combined with a token limit.

---

# 4. Recursive chunking

This is one of the most commonly used general-purpose strategies.

The idea is:

> Try to split using the largest meaningful boundary first. If the resulting piece is still too large, recursively split using a smaller boundary.

For example:

```text
Document
   ↓
Paragraph
   ↓
Sentence
   ↓
Word
   ↓
Character
```

Conceptually:

```python
separators = [
    "\n\n",  # paragraph
    "\n",    # line
    ". ",    # sentence
    " ",     # word
    ""       # character
]
```

Simplified implementation:

```python
def recursive_split(text, chunk_size=500):
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", " ", ""]

    for separator in separators:
        parts = text.split(separator)

        if len(parts) == 1:
            continue

        chunks = []
        current = ""

        for part in parts:
            candidate = current + separator + part

            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())

                current = part

        if current:
            chunks.append(current.strip())

        # Recursively split anything still too large
        final_chunks = []

        for chunk in chunks:
            if len(chunk) > chunk_size:
                final_chunks.extend(
                    recursive_split(chunk, chunk_size)
                )
            else:
                final_chunks.append(chunk)

        return final_chunks

    return [text]
```

### Why this is powerful

You don't arbitrarily destroy structure.

For example:

```text
Document
 ├── Section
 │    ├── Paragraph
 │    │    ├── Sentence
 │    │    └── Sentence
 │    └── Paragraph
```

You try to preserve that hierarchy.

---

# 5. Token-based chunking

LLMs operate on tokens, not characters.

Therefore, for production RAG, token-based chunking is often more meaningful.

For example:

```python
import tiktoken

encoder = tiktoken.get_encoding("cl100k_base")

def token_chunks(text, chunk_size=300, overlap=50):

    tokens = encoder.encode(text)

    chunks = []

    start = 0

    while start < len(tokens):

        end = start + chunk_size

        chunk_tokens = tokens[start:end]

        chunks.append(
            encoder.decode(chunk_tokens)
        )

        if end >= len(tokens):
            break

        start = end - overlap

    return chunks
```

Now your constraint is:

```text
Chunk ≤ 300 tokens
Overlap = 50 tokens
```

rather than:

```text
Chunk ≤ 1000 characters
```

### Why this matters

Suppose your embedding model has a token limit.

You don't want:

```text
3000 characters
```

to be your assumption of chunk size because different languages and content have different token densities.

---

# 6. Semantic chunking

This is more advanced.

Instead of asking:

> "Where should I split based on characters?"

you ask:

> "Where does the meaning of the text change?"

For example:

```text
The customer created an account in 2022.
The customer upgraded to premium in 2023.
The customer cancelled the subscription in 2025.

--------------------------------------------

The application is hosted on Azure.
The database runs on PostgreSQL.
Redis is used for caching.
```

A semantic chunker should recognize two different topics.

One common technique:

1. Split into sentences.
2. Generate embeddings for sentences.
3. Calculate similarity between adjacent sentences.
4. Detect large similarity drops.
5. Split there.

Conceptually:

```python
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def semantic_chunks(text, threshold=0.5):

    sentences = [
        s.strip()
        for s in text.split(".")
        if s.strip()
    ]

    embeddings = model.encode(sentences)

    chunks = []
    current = [sentences[0]]

    for i in range(1, len(sentences)):

        similarity = cosine_similarity(
            [embeddings[i - 1]],
            [embeddings[i]]
        )[0][0]

        if similarity < threshold:
            chunks.append(". ".join(current))
            current = []

        current.append(sentences[i])

    if current:
        chunks.append(". ".join(current))

    return chunks
```

### Advantage

Chunks tend to represent coherent concepts.

### Disadvantage

Much more expensive because you're generating embeddings during ingestion.

---

# 7. Structure-aware chunking

For real-world RAG, this is extremely important.

You use the document's structure.

For example:

```text
# Authentication

## OAuth

OAuth allows...

## JWT

JWT is used...

# Database

## PostgreSQL

PostgreSQL supports...
```

You don't want to blindly split this.

Instead:

```text
Chunk
{
    content: "...",
    metadata: {
        heading: "Authentication",
        subsection: "OAuth"
    }
}
```

Python example for Markdown:

```python
def markdown_chunks(text):

    lines = text.splitlines()

    chunks = []

    current_heading = None
    current_content = []

    for line in lines:

        if line.startswith("#"):

            if current_content:
                chunks.append({
                    "content": "\n".join(current_content),
                    "heading": current_heading
                })

            current_heading = line.lstrip("#").strip()
            current_content = []

        else:
            current_content.append(line)

    if current_content:
        chunks.append({
            "content": "\n".join(current_content),
            "heading": current_heading
        })

    return chunks
```

This is much better for:

* Markdown
* HTML
* technical documentation
* API documentation
* knowledge bases

---

# 8. Document-type-aware chunking

This is where production RAG becomes interesting.

Different documents need different strategies.

For example:

| Document       | Strategy             |
| -------------- | -------------------- |
| Markdown       | Heading-aware        |
| HTML           | DOM/heading-aware    |
| PDF            | Layout + paragraph   |
| Word           | Heading/paragraph    |
| Source code    | Function/class based |
| JSON           | Object/record based  |
| CSV            | Row/group based      |
| Email          | Thread/message based |
| Legal document | Section/clause based |
| Logs           | Time/event based     |

For example, source code:

```python
class OrderService:

    def create_order(self):
        ...

    def cancel_order(self):
        ...
```

You generally don't want:

```text
class OrderService:

    def create_order(self):
        ...
    
    def can
```

Instead:

```text
Chunk 1 → OrderService.create_order()
Chunk 2 → OrderService.cancel_order()
```

---

# 9. Parent-child chunking

This is particularly useful for production RAG.

Imagine:

```text
Parent document
      |
      +-- Chunk 1
      +-- Chunk 2
      +-- Chunk 3
      +-- Chunk 4
```

You create small chunks for accurate retrieval.

But when one is retrieved, you can provide the **larger parent context** to the LLM.

Example:

```python
parent = """
The authentication system uses OAuth 2.0.

OAuth provides delegated authorization.

JWT tokens are generated after successful authentication.

Refresh tokens are stored securely.
"""

children = [
    "OAuth provides delegated authorization.",
    "JWT tokens are generated after successful authentication."
]
```

Vector DB stores:

```text
child chunk
embedding
parent_id
```

Retrieval:

```text
query
 ↓
child chunk retrieved
 ↓
parent_id
 ↓
fetch parent context
 ↓
LLM
```

This solves an important trade-off:

> Small chunks improve retrieval precision, while larger context improves answer completeness.

---

# 10. Agent/LLM-assisted chunking

You can even use an LLM to identify logical boundaries.

For example:

```text
Input document
      ↓
LLM
      ↓
Identify topics
      ↓
Generate sections
      ↓
Chunks
```

Prompt concept:

```python
prompt = """
Analyze the following document.

Identify logical topic boundaries.
Create chunks where each chunk represents one coherent concept.

Do not split sentences.
Do not exceed 500 tokens per chunk.

Return JSON:
[
  {
    "topic": "...",
    "content": "..."
  }
]
"""
```

This can work very well for complex documents but increases:

* latency
* ingestion cost
* complexity
* failure modes

I wouldn't use an LLM for every document by default.

---

# The important question: Can this be dynamic?

**Absolutely.**

And this is actually how I'd design it for your production RAG architecture.

Instead of:

```python
chunk_document(document)
```

build:

```python
chunk_document(
    document,
    strategy="recursive",
    chunk_size=500,
    overlap=50
)
```

But go one step further.

---

# Dynamic Chunking Architecture

I'd introduce a `ChunkingStrategy` abstraction.

```python
from abc import ABC, abstractmethod


class ChunkingStrategy(ABC):

    @abstractmethod
    def chunk(self, document):
        pass
```

Then:

```python
class FixedChunker(ChunkingStrategy):

    def chunk(self, document):
        ...


class RecursiveChunker(ChunkingStrategy):

    def chunk(self, document):
        ...


class SemanticChunker(ChunkingStrategy):

    def chunk(self, document):
        ...


class MarkdownChunker(ChunkingStrategy):

    def chunk(self, document):
        ...


class CodeChunker(ChunkingStrategy):

    def chunk(self, document):
        ...
```

Then use a factory:

```python
class ChunkerFactory:

    @staticmethod
    def create(document_type, strategy):

        if strategy == "fixed":
            return FixedChunker()

        if strategy == "recursive":
            return RecursiveChunker()

        if strategy == "semantic":
            return SemanticChunker()

        if document_type == "markdown":
            return MarkdownChunker()

        if document_type == "code":
            return CodeChunker()

        raise ValueError("Unsupported strategy")
```

---

# But I would make it configuration-driven

Instead of changing code:

```json
{
  "documentType": "markdown",
  "chunking": {
    "strategy": "recursive",
    "chunkSize": 500,
    "overlap": 50
  }
}
```

Another customer:

```json
{
  "documentType": "pdf",
  "chunking": {
    "strategy": "semantic",
    "chunkSize": 400,
    "overlap": 50
  }
}
```

Another:

```json
{
  "documentType": "source-code",
  "chunking": {
    "strategy": "function"
  }
}
```

Your ingestion pipeline becomes:

```text
                 ┌───────────────┐
Document ───────►│ Document      │
                 │ Classifier    │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Chunking      │
                 │ Configuration │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Chunking      │
                 │ Strategy      │
                 └───────┬───────┘
                         │
              ┌──────────┼───────────┐
              ▼          ▼           ▼
          Recursive   Semantic    Structure
              │          │           │
              └──────────┼───────────┘
                         ▼
                    Chunk objects
                         │
                         ▼
                     Embedding
                         │
                         ▼
                     Vector DB
```

---

# What should a Chunk object contain?

This connects directly with your previous question about **document metadata vs chunks**.

I would create something like:

```python
chunk = {
    "chunk_id": "doc123_chunk_007",

    "document_id": "doc123",

    "content": "...",

    "metadata": {
        "document_name": "architecture.pdf",
        "document_version": 4,
        "page_number": 27,
        "section": "Authentication",
        "heading": "OAuth",
        "chunk_index": 7
    },

    "chunking": {
        "strategy": "recursive",
        "chunk_size": 500,
        "overlap": 50
    }
}
```

And importantly:

```text
Document metadata
       │
       │ document_id
       ▼
Document Store
       │
       │
       ▼
Chunk metadata ───────► Vector DB
       │
       └───────────────► Object/Document Store
```

---

# How much work is dynamic chunking?

For an interview, I'd break the implementation into **5 levels**.

### Level 1 — Basic

Implement:

```text
Fixed
Sentence
Paragraph
Recursive
```

**Effort:** ~1–2 days.

---

### Level 2 — Production basic

Add:

```text
Token-based splitting
Metadata
Overlap
Document IDs
Chunk IDs
Versioning
Hashing
```

Architecture:

```text
Document
 ↓
Parser
 ↓
Chunker
 ↓
Metadata enrichment
 ↓
Embedding
 ↓
Vector DB
```

**Effort:** ~3–5 days.

---

### Level 3 — Document-aware

Add:

```text
PDF
DOCX
HTML
Markdown
JSON
CSV
Source code
```

with specialized strategies.

**Effort:** ~1–2 weeks depending on parsers and quality requirements.

---

### Level 4 — Semantic

Add:

```text
Sentence extraction
      ↓
Embedding
      ↓
Similarity calculation
      ↓
Boundary detection
      ↓
Semantic chunks
```

Then tune:

```text
similarity threshold
max tokens
minimum chunk size
overlap
```

**Effort:** ~1–2 weeks for a solid implementation and evaluation.

---

### Level 5 — Production intelligent chunking

Now you're building a **chunking platform** rather than just a splitter.

Add:

```text
Document classifier
        ↓
Strategy selection
        ↓
Configuration service
        ↓
Chunking
        ↓
Quality validation
        ↓
Embedding
        ↓
Vector DB
```

And introduce:

### Chunking evaluation

Track:

```text
Retrieval Recall
Precision
Context relevance
Answer faithfulness
Token consumption
Embedding cost
Latency
Duplicate chunks
Orphan chunks
```

Then you can experimentally determine:

```text
PDF → semantic
Markdown → heading + recursive
Code → AST/function
FAQ → question/answer
Logs → event/time window
```

rather than assuming one strategy works for everything.

---

# What I would say in a Principal Engineer interview

A strong answer would be:

> **"I wouldn't use a single chunking strategy for a production RAG system. I'd build chunking as a pluggable strategy with configuration-driven selection. During ingestion, I would first identify the document type and structural characteristics, then select an appropriate chunker such as recursive, semantic, structure-aware, or domain-specific chunking. Every chunk would retain document ID, version, section, page, chunk index and chunking configuration as metadata.**
>
> **For small and stable documents I'd start with recursive token-based chunking. For structured documents I'd preserve headings and hierarchy. For source code I'd chunk at class/function boundaries. For high-value content I'd evaluate semantic or parent-child chunking.**
>
> **Most importantly, I'd evaluate chunking using retrieval metrics rather than assuming a particular chunk size is optimal. Chunk size, overlap and semantic thresholds should be configuration-driven so they can be tuned without changing the ingestion pipeline."**

That answer demonstrates that you understand **RAG as a production system**, rather than just knowing how to call `RecursiveCharacterTextSplitter`.
