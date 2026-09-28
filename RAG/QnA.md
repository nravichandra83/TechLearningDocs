# RAG & GenAI Interview Preparation — 10 Key Questions

## 1. How do you ensure a vector DB retrieves the most relevant context? How do you evaluate retrieval quality?

Answer: I use a combination of effective chunking, embedding selection, metadata filtering, hybrid search, reranking, and retrieval evaluation.

* Chunking: Create semantically coherent chunks with appropriate size and overlap.

* Embedding model: Select an embedding model that captures domain-specific semantic similarity.

* Hybrid search: Combine vector similarity with keyword-based search such as BM25.

* Metadata filtering: Restrict retrieval by department, document type, access permissions, or version.

* Reranking: Use a cross-encoder or reranking model to reorder the top retrieved chunks.

* Top-K tuning: Experiment with the number of chunks retrieved and the similarity threshold.

Evaluation metrics:

| Metric | Purpose | 
| --- | --- |
|Recall@K |Whether relevant chunks appear in the top K results|
|Precision@K | How many retrieved chunks are relevant|
|MRR|How highly the first relevant result is ranked|
|nDCG@K|Evaluates ranking quality, considering relevance levels|

I create a representative question-answer dataset with expected relevant document chunks, evaluate retrieval independently, and tune the pipeline against these metrics.

Key point: A vector database returning results does not guarantee relevant retrieval. Retrieval quality must be measured against a ground-truth evaluation dataset.

## 2. When do you choose RAG vs. fine-tuning?

Answer: I choose based on whether the problem requires additional knowledge or a change in model behavior.

|Requirement|Approach|
| --- | --- |
|Frequently changing business knowledge|RAG|
|Answers grounded in internal documents|RAG|
|Source citations and traceability|RAG|
|Domain-specific response format or style|Fine-tuning|
|Consistent task-specific behavior|Fine-tuning|
|New knowledge that changes frequently|RAG, rather than relying on fine-tuning alone|
|Knowledge-intensive task requiring specific behavior and external facts|RAG + fine-tuning|

RAG retrieves relevant external information at inference time and provides it to the LLM as context.

Fine-tuning updates model parameters using task-specific examples to improve behavior, format, or task performance.

I generally start with RAG when the primary requirement is enterprise knowledge retrieval. I consider fine-tuning when prompt engineering is insufficient to achieve consistent behavior. Both can be combined when required.

## 3. Difference between traditional ML and GenAI/LLMs? What are the major challenges in each?

Answer: Traditional ML primarily learns patterns from data to make predictions, classifications, or numerical estimates. GenAI learns patterns that enable it to generate new content, such as text, code, images, or audio.

|Dimension|Traditional ML|GenAI / LLM|
| --- | --- | --- |
|Primary objective|Prediction or classification|Content generation and reasoning|
|Output|Class, score, probability, numeric value|Text, code, or other generated content|
|Typical training|Task-specific datasets|Large-scale pretraining; optionally fine-tuning|
|Evaluation|Accuracy, precision, recall, F1, RMSE|Task-specific quality, factuality, relevance, safety|
|Explainability|Depends on model; often easier for simpler models|Often difficult to explain|
|Inference cost|Often relatively low|Can be high, especially for large models|
|Common use cases|Fraud detection, forecasting, churn prediction|Summarization, assistants, code generation, RAG|

Major challenges in traditional ML:

* Data quality, missing values, and class imbalance.

* Feature engineering and feature selection.

* Overfitting, underfitting, and data leakage.

* Model drift and production monitoring.

Major challenges in GenAI/LLMs:

* Hallucinations and factual inconsistency.

* Context-window limitations and retrieval quality.

* High inference cost and latency.

* Prompt injection, data leakage, and unsafe outputs.

* Non-deterministic outputs and difficult evaluation.

## 4. How do you decide chunk size in RAG?

Answer: I determine chunk size based on document structure, the embedding model, query patterns, and the LLM's context window. I validate the choice empirically rather than relying on a fixed number.

My approach:

1. Start with a baseline, for example, 500 tokens with 50–100 tokens of overlap.

2. Test smaller chunks for precise fact retrieval and larger chunks for conceptual or procedural questions.

3. Evaluate Recall@K, Precision@K, and answer quality.

4. Measure token usage, retrieval latency, and the amount of irrelevant context.

5. Select the configuration that provides the best balance of retrieval quality, answer quality, cost, and latency.

Trade-off:

|Chunk size|Advantages|Disadvantages|
| --- | --- | --- |
|Small|Better retrieval precision|May lose context|
|Large|Preserves context|May introduce noise and consume more tokens|

The ideal size is task-dependent, not universal.

## 5. What are the different chunking strategies?

Answer: I choose chunking strategies based on the structure and semantics of the source documents.

|Strategy|Description|When to use|
| --- | --- | --- |
|Fixed-size|Splits text after a fixed number of characters or tokens|Simple text and baseline pipelines|
|Recursive|Splits using a hierarchy of separators|General-purpose RAG|
|Semantic|Splits when semantic similarity between adjacent text segments drops|Long-form, concept-oriented content|
|Structure-based|Splits using headings, sections, or document elements|Technical documentation, policies|
|Sentence-based|Groups sentences into chunks|FAQs and concise factual content|
|Document-aware|Uses pages, paragraphs, tables, or document layout|PDFs, reports, manuals|
|Hierarchical|Maintains parent sections and smaller child chunks|Precise retrieval with broader context|
|Agentic/LLM-based|Uses an LLM to identify logical boundaries|Complex documents where simpler methods perform poorly|

In production, I would generally start with recursive, structure-aware chunking and introduce semantic or hierarchical chunking when evaluation demonstrates a need.

## 6. What are the basic retrieval techniques used in RAG?

Answer: The main retrieval techniques are:

|Technique|Description|
| --- | --- |
|Dense retrieval|Uses embeddings to retrieve semantically similar chunks through vector similarity|
|Sparse retrieval|Uses lexical matching, such as BM25, to find documents containing relevant terms|
|Hybrid retrieval|Combines dense and sparse retrieval to capture both semantic meaning and exact keyword matches|
|Metadata-filtered retrieval|Restricts results using attributes such as department, document version, or permissions|
|Reranking|Retrieves an initial candidate set and uses a more accurate model to reorder the results|
|Multi-query retrieval|Generates alternative queries to improve recall|
|Parent-document retrieval|Finds a relevant child chunk and returns its larger parent section for context|

A common production pipeline is:

User query

Hybrid retrieval + metadata filters

Candidate fusion + reranking

Top relevant chunks

LLM generates grounded answer

## 7. How do you debug a RAG system when 3 out of 10 questions return "I don't know"?

Answer: I trace each failed question through the entire RAG pipeline to identify whether the problem is in ingestion, retrieval, context construction, or generation.

|Step|What to check|Possible issue|
| --- | --- | --- |
|1. Reproduce and classify|Capture failed queries, expected answers, and source documents|Unclear failure conditions|
|2. Verify ingestion|Check extraction, chunking, embeddings, and indexing|Missing or outdated documents|
|3. Inspect retrieval|Review top-K chunks, scores, and source IDs|Poor retrieval or embeddings|
|4. Check filters|Verify tenant, department, version, and permissions|Relevant chunks excluded|
|5. Inspect context assembly|Confirm retrieved chunks reach the final prompt|Truncation or context loss|
|6. Inspect generation|Review prompt and LLM response|Prompt or model issue|
|7. Run regression tests|Rerun failed and previously successful queries|Fix introduces new failures|

Detailed approach:

1. Reproduce and classify failures. Capture the three failed questions, expected answers, source documents, and exact pipeline configuration.

2. Verify document ingestion. Check whether the source document was discovered, extracted, chunked, embedded, and indexed correctly.

3. Inspect retrieval results. Run each failed query directly against the retriever. Inspect the top-K chunks, similarity scores, metadata, and source document IDs.

4. Check filters and permissions. Verify that department, tenant, document version, and access-control filters are not excluding valid content.

5. Inspect context assembly. Check whether relevant chunks are truncated, dropped, duplicated, or pushed outside the effective context window.

6. Inspect the prompt and LLM response. Verify whether the prompt is too restrictive, the context is contradictory, or the model fails to use the supplied evidence.

7. Fix and run regression tests. Apply the targeted fix and rerun the failed questions along with the full evaluation suite.

Key point: I would not increase Top-K or change the LLM immediately. I would first identify the failing stage using traces and retrieved-context inspection.

## 8. What are text splitters? What are their types, and when do you use them?

Answer: Text splitters are components that divide extracted documents into smaller pieces suitable for embedding, indexing, and retrieval.

|Text splitter|Description|When to use|
| --- | --- | --- |
|CharacterTextSplitter|Splits based on a character separator and a maximum chunk size|Simple text|
|RecursiveCharacterTextSplitter|Tries separators hierarchically, such as paragraphs, newlines, and spaces|General-purpose RAG|
|Token-based splitter|Enforces chunk limits using model tokens rather than characters|Token-budget control|
|Sentence splitter|Splits at sentence boundaries|Sentence-level retrieval|
|Markdown/HTML splitter|Preserves headings and document structure|Documentation and web content|
|Code splitter|Splits using programming-language structures such as classes and functions|Source code repositories|
|Semantic splitter|Uses embeddings or semantic similarity to identify meaningful boundaries|Concept-oriented documents|

A practical distinction: a text splitter is the implementation used to split text, whereas chunking is the overall process and strategy.

## 9. What is chunking? Explain its parameters.

Answer: Chunking is the process of dividing a document into smaller, meaningful segments that can be independently embedded, indexed, retrieved, and passed to an LLM.

|Parameter|Meaning|
| --- | --- |
|`chunk_size`|Maximum target size of each chunk, measured in characters or tokens|
|`chunk_overlap`|Amount of content shared between consecutive chunks|
|`separators`|Boundaries used for splitting, such as paragraphs or sentences|
|`length_function`|Function used to measure chunk length|
|`keep_separator`|Whether delimiters are retained in the resulting chunks|
|`add_start_index`|Whether to retain the chunk's starting position in the original text|

For example, with a chunk size of 500 tokens and overlap of 50 tokens, consecutive chunks share approximately 50 tokens.

Overlap helps preserve context across boundaries, but excessive overlap increases storage, embedding cost, and duplicate retrieval.

Important: `chunk_size` may be a hard limit or a target, depending on the splitter. Always verify the implementation's behavior.

## 10. How do you select an LLM for a given project?

Answer: I select an LLM based on task performance, quality requirements, latency, cost, security, deployment constraints, and operational requirements—not simply model size or benchmark scores.

|Evaluation criterion|What to assess|
| --- | --- |
|Task performance|Accuracy, reasoning, instruction following|
|Groundedness|Ability to generate answers supported by retrieved context|
|Latency|Response time and time to first token|
|Cost|Input/output token costs and cost per successful task|
|Throughput|Requests per second and concurrency|
|Context window|Ability to handle the required input size|
|Security|Data privacy, residency, and access controls|
|Deployment|Hosted API versus self-hosted model|
|Reliability|Availability, structured-output consistency, and failure handling|

Selection process:

1. Define the use case: RAG, summarization, classification, coding, reasoning, or agentic workflows.

2. Establish evaluation criteria: accuracy, groundedness, instruction following, structured-output reliability, and safety.

3. Shortlist models: compare hosted and self-hosted options, including smaller models for simpler tasks.

4. Run a representative evaluation: use real queries, edge cases, domain-specific examples, and adversarial inputs.

5. Measure operational performance: latency, throughput, token consumption, concurrency, and cost per successful task.

6. Validate enterprise requirements: data residency, privacy, access controls, compliance, and availability.

7. Choose and monitor: deploy the selected model, track production quality, and reassess when requirements or model versions change.

For a RAG application, I evaluate the embedding model, reranker, and generation model separately, because each contributes differently to end-to-end quality.

I also consider routing: a smaller model can handle simple queries, while a more capable model handles complex reasoning or difficult questions.

Final interview takeaway: I treat model selection as an evaluation-driven engineering decision balancing quality, cost, latency, security, and maintainability.

## 11. What are RAG evaluations? Explain each. Can RAGAS measure all of them? What are the alternatives?

Interview answer:

RAG evaluation is the process of measuring how effectively a RAG pipeline retrieves relevant information, generates accurate and grounded answers, and satisfies the user's query.

I evaluate RAG at three levels: retrieval quality, generation quality, and end-to-end performance.

### A. RAG evaluation metrics

|Metric|What it measures|Example|
| --- | --- | --- |
|Context Precision|Whether relevant chunks are ranked above irrelevant chunks|Relevant chunks appear near the top|
|Context Recall|Whether the retrieved context contains the information needed to answer|All required facts are retrieved|
|Faithfulness|Whether the answer is supported by the retrieved context|No unsupported claims|
|Answer Relevancy|Whether the answer addresses the user's question|No irrelevant or off-topic response|
|Answer Correctness|Whether the answer matches the reference answer|Correct facts and conclusions|
|Context Relevancy|How relevant the retrieved context is to the query|Minimal irrelevant content|
|Retrieval Recall@K|Whether relevant documents appear in the top K results|Relevant evidence is retrieved|
|MRR / nDCG@K|How well relevant results are ranked|Relevant chunks rank higher|

The first six are common RAG evaluation dimensions; the last two are standard information-retrieval metrics.

### B. Can RAGAS measure all of them?

Ragas supports many RAG-specific metrics, including context precision, context recall, faithfulness, answer relevancy, and answer correctness. Its exact metric set depends on the version and evaluation configuration.

However, Ragas does not automatically cover every aspect of a production RAG system.

|Evaluation area|Ragas suitability|Additional evaluation needed|
| --- | --- | --- |
|Retrieval relevance|Strong|Ground-truth Recall@K, MRR, nDCG|
|Answer faithfulness|Strong|Human review for critical use cases|
|Answer correctness|Supported|Domain-expert validation|
|Hallucination detection|Partially covered through faithfulness|Independent factual verification|
|Latency and throughput|Not its primary purpose|Load testing and telemetry|
|Cost per query|Not its primary purpose|Token and API cost tracking|
|Access-control correctness|Not sufficient by itself|Security and authorization tests|
|Production reliability|Not sufficient by itself|Integration and operational monitoring|

### C. What are the alternatives?

|Framework / approach|Primary use|
| --- | --- |
|Ragas|RAG-specific evaluation metrics|
|DeepEval|LLM and RAG evaluation, test cases, and regression testing|
|TruLens|RAG evaluation and feedback-based observability|
|LangSmith|Tracing, datasets, experiments, and evaluation workflows|
|Arize Phoenix|Tracing, retrieval analysis, and LLM observability|
|Custom evaluation pipeline|Domain-specific metrics, business rules, and ground-truth validation|

My approach: I use Ragas or a similar framework for automated evaluation, maintain a curated dataset of questions and expected evidence, add domain-expert reviews for critical scenarios, and track latency, cost, and production failures separately.


## 12. How do you handle table data during RAG ingestion?

Interview answer:

Tables require special handling because extracting their text without preserving row-column relationships can destroy their meaning. I preserve the table structure during ingestion and convert it into a representation that supports accurate retrieval.

### My approach

1. Extract: Use layout-aware parsers to identify tables, headers, rows, merged cells, and captions.

2. Normalize: Handle merged cells, repeated headers, multi-page tables, and inconsistent formatting.

3. Preserve relationships: Keep column names associated with their corresponding values.

4. Chunk: Split large tables by logical groups of rows, repeating the headers in each chunk.

5. Enrich metadata: Store document ID, page number, table ID, section, and applicable business metadata.

6. Index: Embed the table representation and, where useful, index the original structured data separately.

7. Retrieve and generate: Return the relevant rows with headers and instruct the LLM to answer using the retrieved data.

### Example

Original table:

| Product | Region | Revenue |
| ------- | ------ | ------- |
| Laptop  | India  | 500000  |
| Mobile  | India  | 300000  |
| Laptop  | US     | 700000  |

A plain-text representation could be:

```
Product: Laptop | Region: India | Revenue: 500000
Product: Mobile | Region: India | Revenue: 300000
Product: Laptop | Region: US | Revenue: 700000
```

This preserves the relationship between each value and its column.

### Which approach should I choose?

| Table type                            | Recommended approach                                        |
| ------------------------------------- | ----------------------------------------------------------- |
| Small, simple tables                  | Convert to Markdown or structured text                      |
| Large tables                          | Chunk by rows or logical groups, retaining headers          |
| Complex tables with merged cells      | Layout-aware extraction and normalization                   |
| Numerical or aggregation-heavy tables | Store in SQL or a structured data store and query using SQL |
| Tables with narrative explanations    | Index both the table and its surrounding text               |

Key point: Vector search is useful for finding relevant table content, but SQL or another structured query engine is generally more reliable for exact filtering, joins, and numerical aggregations.

## 13. How do you evaluate LLM responses in Agentic AI and RAG?

Interview answer:

I evaluate the system at multiple levels: output quality, grounding, task completion, intermediate decisions, tool execution, and operational performance.

### A. RAG evaluation

| Dimension          | What I evaluate                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------ |
| Retrieval quality  | Were the correct chunks retrieved?                                                         |
| Faithfulness       | Is the answer supported by the retrieved context?                                          |
| Answer correctness | Is the answer factually correct?                                                           |
| Answer relevancy   | Does the answer address the question?                                                      |
| Completeness       | Does the answer cover all required facts?                                                  |
| Safety             | Does the response avoid leaking sensitive information or following malicious instructions? |

I use a combination of reference-based evaluation, LLM-as-a-judge, deterministic checks, and human review.

### B. Agentic AI evaluation

| Dimension             | What I evaluate                                              |
| --------------------- | ------------------------------------------------------------ |
| Task completion       | Did the agent achieve the requested goal?                    |
| Tool selection        | Did it choose the correct tool?                              |
| Argument correctness  | Were the tool inputs correct?                                |
| Execution correctness | Did the tool produce the intended result?                    |
| Planning              | Were the steps appropriate for the task?                     |
| Trajectory quality    | Was the sequence of actions appropriate?                     |
| Efficiency            | Were unnecessary steps, tool calls, or retries avoided?      |
| Safety                | Did the agent respect permissions and approval requirements? |

### C. How I implement evaluation

1. Create a golden dataset of representative tasks and expected outcomes.

2. Capture traces containing prompts, retrieved chunks, tool calls, arguments, outputs, and final responses.

3. Run automated evaluations using frameworks such as Ragas or DeepEval.

4. Add deterministic assertions for structured outputs, permissions, tool arguments, and business rules.

5. Use human review for ambiguous or high-impact cases.

6. Track quality, latency, cost, failure rates, and regression results across releases.

For agentic systems, I evaluate the complete execution trajectory, not just the final response. An agent may produce a plausible answer while using the wrong tool or performing an unauthorized action.

Ragas supports agent-oriented metrics such as tool-call accuracy and agent-goal accuracy. DeepEval also provides task-completion and tool-correctness metrics.



## 14. When do you implement multi-query retrieval in RAG?

Interview answer:

I implement multi-query retrieval when a single user query does not retrieve sufficient relevant context because of vocabulary differences, ambiguity, or multiple interpretations.

The approach is to generate multiple semantically different queries from the original question, retrieve results for each query, and combine the results.

### Example

Original query: "How do I reduce database response time?"

Generated queries:

* How can I optimize SQL query performance?

* What indexing strategies reduce database latency?

* How can I identify database bottlenecks?

Each query retrieves relevant chunks, and the results are combined.

### When to use it

| Scenario                                            | Multi-query retrieval |
| --------------------------------------------------- | --------------------- |
| User uses different terminology from the documents  | Useful                |
| Query is ambiguous                                  | Useful                |
| Question involves multiple concepts                 | Useful                |
| Initial retrieval has low recall                    | Useful                |
| Exact ID, order number, or unique identifier lookup | Usually unnecessary   |
| Latency-sensitive, simple factual queries           | Often unnecessary     |

Trade-off: Multi-query retrieval can improve recall, but it increases retrieval operations, latency, and potentially the amount of irrelevant context.

I evaluate whether it improves Recall@K and answer quality enough to justify the additional cost.

## 15. What is candidate fusion?

Interview answer:

Candidate fusion is the process of combining search results from multiple retrieval queries or retrieval systems into a single candidate list.

For example, dense retrieval may return 20 chunks, while BM25 returns another 20. Candidate fusion combines these lists, handles duplicates, and produces a unified ranking.

### Common fusion techniques

| Technique                    | How it works                                                                 |
| ---------------------------- | ---------------------------------------------------------------------------- |
| Reciprocal Rank Fusion (RRF) | Combines rankings using the reciprocal of each document's rank               |
| Weighted score fusion        | Combines normalized relevance scores using configurable weights              |
| Rank-based fusion            | Combines rankings using rank positions                                       |
| Union with deduplication     | Combines candidate sets and removes duplicates; ranking may happen afterward |

RRF is particularly useful when different retrievers produce scores on incompatible scales.

A common RRF formula is:

RRF⁡(d)=∑r∈R1k+rank⁡r(d)\operatorname{RRF}(d)= \sum_{r \in R}\frac{1}{k+\operatorname{rank}_r(d)}RRF(d)=r∈R∑k+rankr(d)1

Here, ddd is a document, RRR is the set of ranked result lists, and kkk is a smoothing constant.

Key point: Candidate fusion combines results from multiple sources; it does not necessarily determine the final relevance ranking using the original query and document content.


## 16. Fusion vs. reranking — what is the difference?

Interview answer:

Fusion combines candidate rankings from multiple retrieval sources, whereas reranking evaluates the retrieved candidates against the query to produce a more relevance-focused ordering.

| Dimension                       | Candidate fusion                         | Reranking                                          |
| ------------------------------- | ---------------------------------------- | -------------------------------------------------- |
| Purpose                         | Combine multiple result lists            | Improve the ordering of retrieved candidates       |
| Input                           | Multiple ranked lists                    | Query and candidate documents                      |
| Typical method                  | RRF, weighted score fusion               | Cross-encoder, reranker LLM                        |
| Uses query-document interaction | Not necessarily                          | Yes, typically                                     |
| Computational cost              | Usually low                              | Higher                                             |
| Main benefit                    | Combines complementary retrieval results | Improves relevance ranking                         |
| Limitation                      | May retain weak candidates               | Cannot recover documents that were never retrieved |

### Example

Suppose dense search and BM25 return different results.

* Dense search finds semantically similar documents.

* BM25 finds documents containing exact keywords.

* Fusion combines these results into one candidate list.

* Reranking evaluates the candidates against the original question and reorders them.

A typical pipeline is:

`Dense + BM25 → Candidate fusion → Reranking → Top-K context → LLM`

Important: Fusion and reranking are complementary, not competing techniques.

## 17. When do you use reranking and hybrid search?

Interview answer:

I use hybrid search when either semantic similarity or keyword matching alone is insufficient. I use reranking when the initial retrieval results need more accurate relevance ordering.

### When to use each

| Scenario                                               | Hybrid search                | Reranking                          |
| ------------------------------------------------------ | ---------------------------- | ---------------------------------- |
| Queries contain exact product names or technical terms | Useful                       | Can improve ordering               |
| Users describe concepts differently from the documents | Useful                       | Can improve ordering               |
| Dense search misses exact keyword matches              | Useful                       | Cannot recover missing candidates  |
| Initial results contain irrelevant chunks              | May help                     | Particularly useful                |
| Multiple retrieval sources are available               | Useful                       | Can rerank the combined candidates |
| Strict latency or cost budget                          | Often relatively inexpensive | Adds inference cost and latency    |

### How I combine them

1. Run dense retrieval and BM25 in parallel.

2. Fuse the candidate lists using RRF.

3. Rerank the top 20–100 candidates, depending on latency and cost constraints.

4. Pass the best few chunks to the LLM.

The candidate counts are starting points, not fixed rules.

Key distinction: Hybrid search improves candidate discovery; reranking improves candidate ordering. Neither guarantees that the correct answer exists in the indexed documents.

## 18. What are temperature, top-p, and top-k in an LLM?

Interview answer:

Temperature, top-p, and top-k are decoding parameters that influence how an LLM selects its next token. They affect the diversity and predictability of generated responses.

### A. Temperature

Temperature adjusts the sharpness of the token probability distribution.

| Temperature          | Effect                   | Typical use                        |
| -------------------- | ------------------------ | ---------------------------------- |
| Low, e.g. 0–0.3      | More predictable outputs | Factual Q&A, structured extraction |
| Medium, e.g. 0.4–0.7 | Moderate variation       | General assistants                 |
| High, e.g. 0.8–1.0+  | More diverse outputs     | Creative writing and brainstorming |

A temperature of zero generally makes output more deterministic, but exact reproducibility is not guaranteed across all model implementations.

### B. Top-p (nucleus sampling)

Top-p selects from the smallest set of tokens whose cumulative probability reaches a specified threshold.

| Top-p | Effect                                                   |
| ----- | -------------------------------------------------------- |
| Low   | Restricts selection to a smaller, higher-probability set |
| High  | Allows a broader set of candidate tokens                 |
| 1.0   | Does not restrict candidates through nucleus sampling    |

For example, with `top_p = 0.9`, the model considers the smallest set of candidate tokens whose cumulative probability reaches 90%.

### C. Top-k sampling

Top-k restricts token selection to the K most probable next tokens.

| Top-k    | Effect                                           |
| -------- | ------------------------------------------------ |
| 1        | Selects the highest-probability token            |
| 10       | Samples from at most the 10 most probable tokens |
| 50       | Allows a broader candidate set                   |
| Disabled | No top-k restriction                             |

### D. Quick comparison

| Parameter   | Controls                           | Main effect                      |
| ----------- | ---------------------------------- | -------------------------------- |
| Temperature | Probability distribution sharpness | Predictability versus randomness |
| Top-p       | Cumulative probability threshold   | Dynamic candidate-set size       |
| Top-k       | Number of candidate tokens         | Fixed candidate-set size         |

Practical recommendation: For a RAG application, I generally start with a low temperature to encourage consistent, grounded responses. I tune top-p or top-k only when the model and API support them and evaluation shows a benefit.

These parameters influence generation behavior; they do not directly improve retrieval accuracy or guarantee factual correctness.