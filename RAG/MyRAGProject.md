# My RAG Project — GenAI Product Knowledgebase Assistant

> **Profile line:** Architected and delivered a GenAI-enabled product knowledgebase assistant leveraging enterprise documentation, business requirements and functional specifications to provide contextual, conversational product intelligence.

---

## 1. Résumé / Profile Version (Short)

**GenAI Product Knowledgebase Assistant (RAG)**

I designed and built a retrieval-augmented generation (RAG) pipeline that turns enterprise product documentation, business requirement documents and functional specifications (PDF, Word, Markdown) into a conversational knowledge assistant. It parses documents with their structure intact, chunks text, tables and images differently, stores embeddings in ChromaDB, and answers questions with Gemini using only the retrieved content, so answers stay grounded and traceable to their source. The ingestion layer is modular, embedding backends can be swapped, and a built-in retrieval check confirms content can be found after ingestion.

---

## 2. Interview Version (2-Minute Walkthrough)

### Problem
Product knowledge was spread across long PDFs, Word specs and requirement documents. People needed fast, accurate answers like "what's the spec for X?" or "which variant supports Y?" without reading 100+ pages. A plain LLM would hallucinate, and naive RAG broke on tables and document structure.

### Solution — Parse → Chunk → Embed → Store/Retrieve → Generate

```
loaders.py  ->  chunking.py  ->  embeddings.py  ->  vectorstore.py  ->  Gemini (grounded answer)
 (parse)        (chunk)          (embed)            (persist/query)
                    |
          table_handler.py / image_handler.py
          (type-specific chunk formatting)
```

1. **Structure-first parsing.** Every format becomes one block model (`text` / `table` / `heading` / `image`). PDFs have no semantic tags, so headings are worked out from font-size heuristics, and repeated headers and footers are removed so they don't pollute retrieval.
2. **Chunking by content type.**
   - Text uses token-aware sliding windows (tiktoken `cl100k_base`, **300 tokens, 50-token overlap**), with the current section heading added to each chunk (`Section: ...`) so it keeps its context.
   - Each table gets one summary chunk plus **one natural-language sentence per row** (`col = value; ...`). A single spec row can be retrieved and understood without the rest of the table. This was the biggest accuracy gain for spec-heavy documents.
   - Images get caption chunks with the absolute image path in metadata. The captioner can be swapped for a vision LLM.
3. **Semantic embeddings.** Chunks and queries are embedded with OpenAI **`text-embedding-3-small`** (1536 dimensions). The same model is used at ingest and query time. The embedding layer sits behind one interface, so the model can be swapped (for example, `text-embedding-3-large` or an open-source BGE model) without touching the rest of the pipeline.
4. **Idempotent vector store.** ChromaDB `PersistentClient`, with chunk IDs built as `sha1(source-index-first50chars)` and `upsert` instead of `add`. Re-ingesting a document doesn't create duplicates.
5. **Grounded generation.** Gemini (`gemini-3.6-flash`, configurable via `GEMINI_MODEL`) runs under a strict system prompt that allows answers only from the retrieved context (**top-k = 8**). If the LLM call fails, the user still sees the raw retrieved chunks.
6. **Self-verification.** After ingestion, the pipeline generates sample questions from the chunks themselves and checks that the source chunk comes back in the top-k results. This proves retrievability, not just that the write succeeded.

### Next Step
A RAGAs-based evaluation harness to measure **faithfulness, answer relevancy, context precision and context recall**.

---

## 3. Key Numbers to Quote

| Parameter | Value | Where |
|---|---|---|
| Chunk size | 300 tokens | `chunking.py` |
| Chunk overlap | 50 tokens | `chunking.py` |
| Tokenizer | tiktoken `cl100k_base` | `chunking.py` |
| Retrieval top-k (Q&A loop) | 8 | `pipeline.py` |
| Embedding model | OpenAI `text-embedding-3-small` (1536 dims) | `embeddings.py` |
| Vector DB | ChromaDB (local persistent; also tested as Podman server) | `vectorstore.py` |
| LLM | Gemini `gemini-3.6-flash` (env-configurable) | `pipeline.py` |
| Chunk ID | `sha1(source-index-first50chars)` + upsert | `vectorstore.py` |

---

## 4. Strengths to Emphasize

| Theme | What to say |
|---|---|
| Architecture | Modular, single-responsibility stages; backends swap without rewrites |
| Data quality | "Garbage in, garbage out": structure-aware parsing and table-row chunks |
| Trust | Grounded prompting and source traceability to reduce hallucination |
| Engineering rigor | Idempotent ingestion, post-ingest retrieval checks, evaluation roadmap |
| Pragmatism | Designed to run within real enterprise limits (offline, restricted network) |

> **Caution:** Don't claim numbers you haven't measured (for example, "40% faster lookups"). Once the RAGAs evaluation is running, add real scores. Measured numbers carry more weight in interviews than invented ones.

---

## 5. Likely Follow-Up Questions & Answers

### 5.1 Architecture & Design

**Q: Walk me through the end-to-end flow.**
Documents are parsed into structured blocks, then chunked differently for text, tables and images. The chunks are embedded and upserted into ChromaDB. At query time the question is embedded, the top-k chunks are retrieved, and Gemini answers using only that context.

**Q: Why build your own pipeline instead of LangChain/LlamaIndex?**
To have full control over parsing and chunking, which is where most RAG quality is won or lost. I wanted table-aware and heading-aware logic that generic loaders don't do well. Frameworks are fine for wiring things together, but the core value here was custom.

**Q: How would you scale this to 100k documents?**
- Run ingestion as batch or async workers with a queue
- Move to a managed vector DB (or Chroma in server mode, which I already tested via Podman)
- Do incremental ingestion using content hashes
- Shard collections by product or domain
- Add caching for frequent queries

**Q: Why ChromaDB?**
It's lightweight, runs both embedded and as a server, supports metadata, and is good for building quickly. In production I'd evaluate pgvector, Qdrant, Weaviate or Azure AI Search based on filtering needs, hybrid search, ops maturity and security.

### 5.2 Parsing & Chunking (Strongest Area — Expect Depth)

**Q: How do you detect headings in a PDF?**
PDFs carry no semantic tags. I find the body font size (the most common one) and treat noticeably larger text as headings. Repeated lines across pages are detected and removed as headers or footers.

**Q: What chunk size and overlap did you use, and why?**
300 tokens with a 50-token overlap, measured with tiktoken. Overlap keeps sentences that span boundaries retrievable. 300 tokens is small enough for precise retrieval but large enough to keep meaning, and I'd tune it with evaluation scores.

**Q: Why prepend the section heading to chunks?**
A chunk like "torque is 200 Nm" means nothing without the "Engine Specifications" heading above it. The prefix restores that context for both the embedding and the LLM.

**Q: How do you handle tables?**
Each table gets one summary chunk plus one sentence per row with the column names inline. A summary-style question matches the whole table, and a specific question matches one row exactly. Tables are never split mid-row.

**Q: How did you generate the summary for tables and the row sentences? Did you use an LLM?**
No. It's rule-based, with no LLM call. That keeps it fast, free, repeatable, and free of hallucination at ingest time.
1. The parser turns each table into a markdown table, and the handler splits it into a **header** and **rows**.
2. A **context prefix** is built from the nearest section heading and the table caption, for example `Section: Engine Specifications. Table: Variant Specs.`
3. **Summary chunk:** the prefix, the column list, and the full table as markdown. This answers overview questions like "what specs are listed?"
4. **Row chunks:** the first column is treated as the row key, and each row becomes a sentence:
   `Section: Engine Specifications. Row where Variant is ZXi: Variant = ZXi; Engine = 1.5L; Power = 103 PS.`
   Every row carries its column names and section, so it makes sense on its own when retrieved.

*Trade-off and next step:* for very wide or complex tables (merged cells, multi-level headers), an LLM-written summary could describe the table more naturally. I'd generate it once at ingest and keep the deterministic row sentences for exact lookups.

**Q: What about images and diagrams?**
Images get a caption chunk plus their file path in the metadata. The default captioner is a stub (filename + alt text). A vision-LLM captioner can be swapped in, so diagram content becomes searchable.

**Q: Scanned PDFs?**
They aren't handled yet. I'd add OCR (Tesseract, or a cloud document AI service) as a fallback when a page has no extractable text.

### 5.3 Embeddings & Retrieval

**Q: Which embedding model did you use, and why?**
OpenAI `text-embedding-3-small` (1536 dimensions). It gives strong semantic quality at very low cost per token, it's fast, and it's a managed API with no GPU to host. `text-embedding-3-large` is more accurate but costs more and stores more data. For product specs and requirement documents, the small model was a good balance between cost and accuracy.

**Q: Can you reduce the embedding dimensions?**
Yes. The text-embedding-3 models support a `dimensions` parameter (for example, 512) that shortens the vectors with only a small quality loss. That cuts storage and speeds up search.

**Q: Which distance metric?**
Cosine similarity. OpenAI embeddings are normalized to unit length, so cosine and dot product give the same ranking.

**Q: Data privacy with an external embedding API?**
Document text is sent to OpenAI. Mitigations: enterprise or zero-data-retention agreements, PII redaction before embedding, or an Azure OpenAI deployment inside the company's tenant.

**Q: Lexical vs. semantic embeddings — trade-offs?**
Lexical methods (BM25, TF-IDF) match exact words: they're great for part numbers and codes but miss synonyms. Semantic embeddings (like `text-embedding-3-small`) match meaning, so "fuel efficiency" finds "mileage", but they can blur exact identifiers. That's why hybrid search (BM25 + embeddings) is the right next step.

**Q: What if you change the embedding model?**
You must re-embed everything. Vectors from different models aren't comparable, and mixing them degrades retrieval without any error. I'd store the model name in the collection metadata and check it at query time.

**Q: How would you improve retrieval quality?**
- Hybrid BM25 + dense retrieval
- A cross-encoder re-ranker
- Metadata filters (document type, product, version)
- Query rewriting or multi-query expansion
- Parent-child chunking (retrieve a small chunk, return its larger parent)

**Q: How did you pick top-k?**
It's a trade-off between recall and noise and context-window cost. I use 8 in the Q&A loop and would tune it with context precision and recall metrics.

### 5.4 Generation & Hallucination

**Q: How do you stop the LLM from making things up?**
- A strict system prompt: answer only from the context, and say "I don't know" otherwise
- Grounding on the retrieved chunks
- Showing the source chunks to the user
- Measuring faithfulness with RAGAs

**Q: What happens when retrieval returns nothing relevant?**
The prompt tells the model to say the answer isn't in the documentation instead of guessing. A similarity threshold could also short-circuit the LLM call.

**Q: Why Gemini?**
Cost and latency were reasonable for Q&A, and access was available. The LLM call is isolated, so swapping to Claude, GPT or a local model is a single-function change.

**Q: How do you handle multi-turn conversation?**
The current loop is single-turn. Next I'd add conversation memory and rewrite follow-ups into standalone questions ("what about the diesel one?" becomes "what is the mileage of the diesel variant?").

### 5.5 Evaluation & Quality

**Q: How do you know it works?**
Two layers:
1. A post-ingest self-check: questions generated from the chunks, verifying each source chunk comes back in the top-k.
2. A RAGAs evaluation (in progress) measuring faithfulness, answer relevancy, context precision and context recall against a golden question set.

**Q: Where would a golden dataset come from?**
SMEs and product owners writing real questions, plus LLM-generated question-answer pairs that are reviewed by humans. It should cover tables, cross-section questions and "not in docs" cases.

**Q: What metrics would you show the business?**
Answer accuracy and faithfulness scores, deflection rate (questions answered without escalation), time saved per lookup, and user feedback (thumbs up/down).

### 5.6 Enterprise & Production Concerns

**Q: Security and access control?**
- Document-level access control lists stored as chunk metadata and filtered at query time, so users only retrieve what they're allowed to see
- PII redaction at ingest
- Secrets kept in env/vault (API keys are in `.env` today)

**Q: How do you keep the knowledge base up to date?**
Content-hash IDs make re-ingestion idempotent. On top of that I'd add change detection, deletion of stale chunks when a document is removed, and version metadata.

**Q: Conflicting info across document versions?**
Tag chunks with version and date, filter or boost the latest, and surface the source so users can see which document an answer came from.

**Q: Cost control?**
- Cache embeddings (they're computed once at ingest)
- Cache frequent answers
- Use smaller or flash models
- Limit context size with re-ranking

**Q: Monitoring?**
Log each query, the retrieved chunks, the answer, latency and feedback. Track retrieval misses and periodically re-run the evaluation to catch regressions.

### 5.7 Behavioral / Ownership

- **"What was the hardest problem?"** Tables in PDFs, and getting the structure right from untagged PDFs. Explain the row-sentence idea.
- **"What would you do differently?"** Start with an evaluation set on day one, and use hybrid retrieval from the start.
- **"What was your specific role?"** I architected and built it end to end: parsing, chunking strategy, the vector store, LLM integration and the verification approach.
- **"How did you get stakeholder buy-in?"** Prepare a real example: a demo answering spec questions with the source shown.

---

## 6. Future Roadmap (Good Closing Talking Point)

- [ ] RAGAs evaluation harness with a golden question set
- [ ] Evaluate `text-embedding-3-large` / reduced dimensions against RAGAs scores
- [ ] Hybrid retrieval (BM25 + dense) and cross-encoder re-ranking
- [ ] Metadata filtering (product, doc type, version) and access control
- [ ] Multi-turn conversation with query rewriting
- [ ] OCR fallback for scanned PDFs; vision-LLM image captioning
- [ ] API / UI layer, monitoring and feedback loop
