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

1. **Structure-first parsing.** Every format becomes one block model (`text` / `table` / `heading` / `image`). For **.docx** (the primary enterprise format: BRDs, functional specs, manuals), headings come from Word paragraph styles, tables are read natively and converted to markdown, and page headers and footers are excluded because they live outside the document body. PDFs have no semantic tags, so headings are worked out from font-size heuristics, and repeated headers and footers are removed. See **Section 3** for the DOCX deep dive.
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

## 3. DOCX Parsing Deep Dive (python-docx)

Most enterprise sources (BRDs, functional specifications, product manuals) were Word documents. Unlike PDF, a `.docx` file is a zip of XML (WordprocessingML), so the structure is **explicit** and doesn't have to be guessed. The goal is to read that structure rather than flatten the file to plain text.

### 3.1 Inside a .docx — what matters

```
document.docx (zip)
├── word/document.xml     ← body: paragraphs <w:p>, tables <w:tbl>, in reading order
├── word/header1.xml      ← page header (separate part)
├── word/footer1.xml      ← page footer (separate part)
├── word/styles.xml       ← "Heading 1", "Heading 2", "Title", "TOC 1", ...
└── word/media/           ← embedded images (referenced by r:embed ids)
```

### 3.2 Walking the body in document order

In python-docx, `doc.paragraphs` and `doc.tables` are **two separate lists**, so they lose where a table sat relative to the text around it. Instead, I walk the raw body XML children in order:

```python
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

def iter_block_items(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)
```

**Why it matters:** each table stays attached to the heading it appears under, so the section context (for example, "Engine Specifications") flows into the table chunks.

### 3.3 Identifying headings and sections

Word stores headings as **paragraph styles**, so detection is exact:

```python
if para.style.name.startswith("Heading"):
    level = int(para.style.name.replace("Heading", "").strip() or 1)
    blocks.append(Block("heading", para.text.strip(), {"level": level}))
```

- Each heading starts a new section, and the text buffered so far is flushed as a block.
- The chunker keeps the **current heading as running context** and adds `Section: <heading>` to every chunk below it.
- The heading level (1, 2, 3) is kept in metadata, so a heading path like `Brakes > ABS > Warning Lights` can be built.

**Edge cases to mention:**
- **Fake headings.** Some authors make headings with **bold + large font** instead of heading styles. The fallback is a run-formatting check: all runs bold, font size above the body size, and a short line. This is the same idea as the PDF font-size heuristic.
- **Custom corporate styles** (e.g. `"BRD Heading 1"`): match against a configurable list of style names, or use the style's outline level.
- **Title and TOC styles.** The `Title` style is treated as the document title, and paragraphs styled `TOC 1/2/3` (the table of contents) are skipped as noise.

### 3.4 Identifying tables and converting them to markdown

Tables are explicit `<w:tbl>` elements, so identification is exact. Conversion:

```python
rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
md_table = rows_to_markdown(rows)

def rows_to_markdown(rows):
    header, *body = rows
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join(["---"] * len(header)) + " |"]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)
```

**Step by step:**
1. Detect `<w:tbl>` during the ordered body walk, and flush any buffered text first so order is kept.
2. Read every row's cells as plain text.
3. Treat the **first row as the header**.
4. Write a markdown table: the header row, a `---` separator row, then one line per body row.
5. Emit a `table` block. The table handler then produces one summary chunk plus one sentence per row (see Section 6.2).

**Example:**

Word table:

| Variant | Engine | Transmission |
|---|---|---|
| LXi | 1.5L K15C | 5MT |
| ZXi+ | 1.5L K15C | 6AT |

Row chunk produced:
`Section: Engine Specifications. Row where Variant is ZXi+: Variant = ZXi+; Engine = 1.5L K15C; Transmission = 6AT.`

**Why markdown?** It gives one common table format across `.md`, `.docx` and `.pdf`, so the downstream table handler is written once. LLMs also read markdown tables very reliably.

**Real-world table gotchas (strong interview material):**

| Problem | What happens | Fix |
|---|---|---|
| Merged cells (horizontal) | python-docx returns the same cell once per grid column, so the text repeats | De-duplicate consecutive identical cells (same `cell._tc`), or keep the repeat on purpose so each column still has a value |
| Merged cells (vertical) | Only the top cell has text, and the cells below look empty | Forward-fill the value down the column |
| Multi-line text in a cell | `\n` breaks the markdown row | Replace newlines with `<br>` or a space |
| Pipe character inside a cell | Breaks the column split | Escape it as `\|` |
| Multi-row headers | The first row alone is incomplete | Combine the header rows (e.g. `Engine / Power`) |
| No real header row | The first data row is used as the header | Detect the header via the "Repeat as header row" property (`w:tblHeader`) or bold formatting |
| Nested tables | `cell.text` flattens them | Recurse into `cell.tables` and render them separately |
| Layout tables (used only for page layout) | Text is mistaken for data | Treat single-column or single-row tables as text, not tables |

### 3.5 Removing noise: headers, footers and repeated boilerplate

**Page headers and footers.** In `.docx` these are stored in **separate XML parts** (`header1.xml`, `footer1.xml`) that each section points to. Because the parser walks only `document.element.body`, page headers, footers, page numbers, document codes and confidentiality lines are **excluded by design**, with no regex or heuristics needed. That's a key advantage over PDF, where they're mixed into the page text.

> If a header carries useful metadata (document ID, version, product name), read it once from `doc.sections[0].header.paragraphs` and attach it to chunks as **metadata**, not as chunk text.

**Repeated boilerplate inside the body.** Some content repeats inside the body itself: disclaimers, "Confidential – Internal Use Only", revision tables, copyright notes, standard "Refer to section X" call-outs, and headers typed by hand instead of using Word's header feature. The approach:

1. **Normalize** each paragraph: lower-case it, collapse whitespace, and replace digits with `#`, so "Page 3 of 42" and "Page 4 of 42" become the same key.
2. **Count** how often each normalized line appears across the document, or across the whole document set.
3. **Drop** lines that are short and repeat more than a threshold, for example in most sections, or in 60%+ of the documents in the corpus. These are classed as **boilerplate**.
4. **Skip known noise** by style or pattern: `TOC` styles, "Revision History" / "Document Control" sections, empty paragraphs, and lines that are only page numbers.

```python
from collections import Counter
import re

def normalize(t):
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", t.strip().lower()))

counts = Counter(normalize(p.text) for p in paragraphs if p.text.strip())
boilerplate = {k for k, c in counts.items() if c >= threshold and len(k) < 150}
clean = [p for p in paragraphs if normalize(p.text) not in boilerplate]
```

The same frequency idea is used for PDFs. There, lines that repeat in the top or bottom margin across most pages are removed as running headers and footers.

**Why it matters:** boilerplate appears in every section, so it matches almost any query and pushes real content out of the top-k. Removing it improves context precision and saves tokens.

### 3.6 Other docx content I handled

- **Text boxes / call-outs.** `paragraph.text` only reads direct text runs, so text inside floating text boxes (`<w:txbxContent>`) is invisible to a normal walk. Manuals use text boxes for **CAUTION / WARNING / NOTE**, so I extract them explicitly and keep each as its own text block (`textbox: True`). Silently dropping safety warnings would be a serious gap.
- **Inline images.** Images are found through `<a:blip r:embed="...">` in each run. The image bytes are read from the related part, saved to `_extracted_images/`, and emitted as `image` blocks with the paragraph text as alt text.
- **Lists.** List paragraphs (`List Bullet`, `List Number`) are kept together in one text block so a step-by-step procedure isn't split across chunks.

### 3.7 DOCX follow-up questions

**Q: Why not just use `docx2txt`, or convert everything to PDF first?**
Both throw away structure. `docx2txt` flattens tables into loose text. Converting to PDF turns exact styles into font sizes that then have to be guessed from. Reading the XML directly keeps headings, tables and order exactly as written.

**Q: How do you keep tables in the right place relative to the text?**
I iterate over the children of `document.element.body` in order instead of using `doc.paragraphs` and `doc.tables` separately.

**Q: How do you identify the header row of a table?**
The first row by default. Stronger signals are the "repeat as header row" flag (`w:tblHeader`), bold formatting, or shading on the first row.

**Q: How do you eliminate footers?**
In docx they live in separate parts, and the body walk never reads them. For boilerplate repeated inside the body, I use normalized-frequency detection and drop lines that repeat across sections or documents.

**Q: What about tracked changes and comments in BRDs?**
Insertions (`<w:ins>`) are included and deletions (`<w:del>`) are excluded, so the text matches the accepted version. Comments are ignored, or stored as metadata if reviewers' notes are valuable.

**Q: How did you validate the parser?**
I compared block counts (headings, tables, images) against `sniff_structure()`, a cheap pre-scan of the document, and spot-checked the generated markdown tables against the source document.

---

## 4. Key Numbers to Quote

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

## 5. Strengths to Emphasize

| Theme | What to say |
|---|---|
| Architecture | Modular, single-responsibility stages; backends swap without rewrites |
| Data quality | "Garbage in, garbage out": structure-aware parsing and table-row chunks |
| Trust | Grounded prompting and source traceability to reduce hallucination |
| Engineering rigor | Idempotent ingestion, post-ingest retrieval checks, evaluation roadmap |
| Pragmatism | Designed to run within real enterprise limits (offline, restricted network) |

> **Caution:** Don't claim numbers you haven't measured (for example, "40% faster lookups"). Once the RAGAs evaluation is running, add real scores. Measured numbers carry more weight in interviews than invented ones.

---

## 6. Likely Follow-Up Questions & Answers

### 6.1 Architecture & Design

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

### 6.2 Parsing & Chunking (Strongest Area — Expect Depth)

> Most sources were **.docx** (BRDs, functional specs, manuals), so expect the deepest questions on Word parsing. Full code and gotchas are in **Section 3**.

**Q: Which document formats did you handle, and which was hardest?**
Mainly .docx, plus PDF and Markdown. All three are parsed into one block model (`text` / `table` / `heading` / `image`), so chunking and embedding are written once. Docx is the richest source because its structure is explicit in the XML. The hard part was the real-world mess inside it: merged table cells, text boxes, repeated boilerplate, and headings faked with bold text.

**Q: How do you parse a .docx file? What library?**
`python-docx`, but not through `doc.paragraphs` and `doc.tables`, because those are two separate lists and lose the order between text and tables. I walk the children of `document.element.body` directly, yielding a `Paragraph` for each `<w:p>` and a `Table` for each `<w:tbl>`. That keeps the reading order exactly as in the document, so each table stays under the heading it belongs to.

**Q: How do you identify headings and sections in a docx?**
From **paragraph styles**: `Heading 1`, `Heading 2` and so on. The number gives the level, which is stored in metadata. Each heading flushes the text buffered so far and becomes the running section context for the chunks below it.
- **Fake headings** (bold or large text in the `Normal` style): fall back to a formatting check: all runs bold, font larger than the body text, short line, no ending period.
- **Custom styles** (e.g. `BRD Heading 1`): a configurable style list, or the style's outline level.
- **Noise styles:** `TOC 1/2/3` (table of contents) is skipped, and `Title` is stored as document metadata.

**Q: How do you identify table data in a docx?**
Tables are explicit `<w:tbl>` elements in the body, so there's nothing to guess. The checks are about whether it's a **real data table**:
- Single-row or single-column tables are usually **layout tables** (used to position content), so they're treated as text.
- The **header row** is the first row by default. Stronger signals are the "repeat as header row" flag (`w:tblHeader`), bold text or shading on that row.
- **Nested tables** inside cells are found through `cell.tables` and handled separately, so they aren't flattened into one cell's text.

**Q: How do you convert a docx table to markdown?**
1. Flush any buffered text so the table keeps its position.
2. Read each row as a list of cell texts (`[cell.text.strip() for cell in row.cells]`).
3. Clean the cells: replace newlines with spaces or `<br>`, escape `|`, and handle merged cells (de-duplicate repeated horizontal merges, forward-fill vertical merges).
4. Write it out: `| h1 | h2 |`, then `| --- | --- |`, then one line per row.
5. Emit a `table` block. The table handler then creates the summary chunk and the row sentences.

Markdown was chosen because it's **one table format** across docx, PDF and Markdown sources, and LLMs read it reliably.

**Q: Merged cells: what goes wrong and how do you fix it?**
python-docx returns a horizontally merged cell **once for every grid column it spans**, so its text repeats across columns. With vertical merges, only the top cell has text and the cells below look empty. Fix: de-duplicate consecutive cells that point to the same underlying XML (`cell._tc`), and forward-fill vertically merged values down the column. Without this, row sentences come out with blank or duplicated values.

**Q: How do you remove headers, footers and other repeated noise?**
Two layers:
1. **Page headers and footers.** In docx they're stored in separate parts (`header1.xml`, `footer1.xml`), not in the body. Because the parser walks only `document.element.body`, they're excluded **by design**. Useful header metadata (document ID, version) can be read once from `doc.sections[0].header` and attached to chunks as metadata.
2. **Boilerplate inside the body** ("Confidential – Internal Use Only", disclaimers, revision history, headers typed manually). Normalize each line (lower-case, collapse whitespace, digits → `#`), count how often it appears across sections or documents, and drop short lines that repeat above a threshold. Known noise sections (`Revision History`, `Document Control`, the table of contents) are skipped by name or style.

*Why it matters:* boilerplate matches almost every query and pushes real content out of the top-k. Removing it improves context precision and saves tokens.

**Q: Is there docx content that a normal parser silently misses?**
Yes:
- **Text boxes.** `paragraph.text` only reads direct runs, so text in floating text boxes (`<w:txbxContent>`) is invisible. Manuals put **CAUTION / WARNING / NOTE** call-outs in text boxes, so I extract them explicitly as their own blocks.
- **Inline images**, found through `<a:blip r:embed>`. The image bytes come from the related part, are saved to disk, and become `image` blocks.
- **Tracked changes.** Insertions (`<w:ins>`) are kept and deletions (`<w:del>`) dropped, so the text matches the accepted version.

**Q: How is PDF parsing different from docx?**
A PDF has no styles and no table or header elements, just positioned text. Headings are inferred from font size (anything noticeably larger than the most common body size). Headers and footers are found by looking for lines that repeat in the top or bottom margin on most pages, with digits normalized so "Page 3 of 42" matches "Page 4 of 42". A docx gives you all of this **exactly**, which is why docx was the more reliable source.

**Q: What chunk size and overlap did you use, and why?**
300 tokens with a 50-token overlap, measured with tiktoken. Overlap keeps sentences that span boundaries retrievable. 300 tokens is small enough for precise retrieval but large enough to keep meaning, and I'd tune it with evaluation scores.

**Q: After chunking, why do we need a tokenizer? Why not just embed chunk by chunk?**
We do embed chunk by chunk. The tokenizer isn't an extra step after chunking. It's used **during** chunking, to decide where each chunk ends.

```
Document text
    │
    ▼
tiktoken: count tokens  ──►  cut every 300 tokens (50-token overlap)   ← chunking
    │
    ▼
Chunk 1, Chunk 2, Chunk 3 ...
    │
    ▼
text-embedding-3-small, one vector per chunk                           ← embedding
```

Why measure chunks in tokens instead of characters or words:
1. **Models count in tokens.** The embedding model's input limit is in tokens (8,191 for `text-embedding-3-small`), and so is the LLM's context window. A character count can't tell you whether a chunk fits.
2. **Characters per token vary a lot.** In plain English one token is about 4 characters, but part numbers, codes and tables (`99011M66T10`, `|---|`) break into many more tokens. A 1,200-character chunk might be 300 tokens or 600.
3. **Cost and context budget.** Embedding cost is per token. With fixed-size token chunks the prompt size is predictable: top-k 8 × 300 ≈ 2,400 tokens of context sent to the LLM.
4. **Consistent retrieval quality.** A huge chunk's vector is diluted across many topics, and a tiny chunk carries too little meaning. Even sizes give even vectors.

*Why tiktoken, if OpenAI tokenizes internally anyway?* The model tokenizes only when you call it, and it doesn't tell you where to split. Chunk boundaries have to be decided before the call. `cl100k_base` is the same tokenizer the `text-embedding-3` models use, so the counts match what the model sees.

*Could you skip it?* Yes, by splitting on characters, sentences or paragraphs, but chunk sizes become unpredictable and you risk going over the limit or wasting context. A common mix is to split on natural boundaries (paragraphs, sentences), then use the token count to merge or cap the pieces.

> **One-liner:** "The tokenizer isn't a separate step after chunking. It's how I measure chunk size, because the embedding model, the LLM and the pricing all work in tokens, and character counts don't map reliably to tokens, especially for codes and tables."

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
Images embedded in docx files are extracted to `_extracted_images/` and get a caption chunk, with the file path stored in the metadata. The paragraph text around the image is used as alt text. The default captioner is a stub (filename + alt text). A vision-LLM captioner can be swapped in, so diagrams and screenshots in specs become searchable.

**Q: Scanned PDFs, or docx files containing pasted screenshots of text?**
They aren't handled yet. I'd add OCR (Tesseract, or a cloud document AI service) as a fallback when a page or image has no extractable text.

### 6.3 Embeddings & Retrieval

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

### 6.4 Generation & Hallucination

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

### 6.5 Evaluation & Quality

**Q: How do you know it works?**
Two layers:
1. A post-ingest self-check: questions generated from the chunks, verifying each source chunk comes back in the top-k.
2. A RAGAs evaluation (in progress) measuring faithfulness, answer relevancy, context precision and context recall against a golden question set.

**Q: Where would a golden dataset come from?**
SMEs and product owners writing real questions, plus LLM-generated question-answer pairs that are reviewed by humans. It should cover tables, cross-section questions and "not in docs" cases.

**Q: What metrics would you show the business?**
Answer accuracy and faithfulness scores, deflection rate (questions answered without escalation), time saved per lookup, and user feedback (thumbs up/down).

### 6.6 Enterprise & Production Concerns

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

### 6.7 Behavioral / Ownership

- **"What was the hardest problem?"** Tables in PDFs, and getting the structure right from untagged PDFs. Explain the row-sentence idea.
- **"What would you do differently?"** Start with an evaluation set on day one, and use hybrid retrieval from the start.
- **"What was your specific role?"** I architected and built it end to end: parsing, chunking strategy, the vector store, LLM integration and the verification approach.
- **"How did you get stakeholder buy-in?"** Prepare a real example: a demo answering spec questions with the source shown.

---

## 7. Future Roadmap (Good Closing Talking Point)

- [ ] RAGAs evaluation harness with a golden question set
- [ ] Evaluate `text-embedding-3-large` / reduced dimensions against RAGAs scores
- [ ] Hybrid retrieval (BM25 + dense) and cross-encoder re-ranking
- [ ] Metadata filtering (product, doc type, version) and access control
- [ ] Multi-turn conversation with query rewriting
- [ ] OCR fallback for scanned PDFs; vision-LLM image captioning
- [ ] API / UI layer, monitoring and feedback loop

---

## 8. Advanced DOCX Table & Heading Questions

> **Theme for all three answers:** every chunk must make sense on its own when retrieved. Tie each parsing decision back to retrieval quality.

### 8.1 How did you handle text in a single-row or single-column table?

In enterprise Word documents, a one-row or one-column table is usually not data. Authors use it for **layout**: a bordered NOTE or WARNING box, a title banner, a definition block, or a vertical list of items. Converting it to a markdown table gives a header with no rows, or a table with one column and no key-value meaning, which produces useless row sentences.

So before converting, I classify each table by shape:

| Shape | What it usually is | How it's handled |
|---|---|---|
| **1 × 1** (single cell) | Call-out box (NOTE / WARNING) | Extracted as a text block with `callout=True` in metadata |
| **1 row, 2 cells** | Label–value pair, e.g. `Document ID \| BRD-104` | Converted to `Document ID: BRD-104` |
| **1 row, 3+ cells** | Banner or strip of labels | Cells joined into one line of text |
| **1 column, many rows** | A list | Joined as bullet lines into one text block under the current heading |
| **2+ rows × 2+ columns** | Real data table | Converted to markdown, then summary chunk + one sentence per row |

```python
n_rows, n_cols = len(table.rows), len(table.columns)
if n_rows == 1 and n_cols == 1:
    emit_text(cell_text, meta={"callout": True})
elif n_rows == 1:
    emit_text(" : ".join(cells) if n_cols == 2 else " | ".join(cells))
elif n_cols == 1:
    emit_text("\n".join(f"- {r}" for r in rows))
else:
    emit_table(rows_to_markdown(rows))
```

> **One-liner:** "I classify tables by shape and meaning, not by XML tag. A `<w:tbl>` doesn't always mean data."

### 8.2 When a table had merged cells, how did you process the data?

Merged cells were the biggest source of bad table chunks. There are two cases.

**Horizontal merge (`gridSpan`).** One cell spans several columns, for example a group header `Engine` spanning `Petrol` and `Diesel`. python-docx's `row.cells` returns the same cell **once for each column it spans**, so its text repeats. I detect this by checking whether consecutive cells point to the same underlying XML element (`cell._tc`):
- **In a header row:** the repeated value is kept on purpose and combined with the sub-header row below. `Engine | Engine` over `Petrol | Diesel` becomes `Engine – Petrol | Engine – Diesel`, so every column has a unique, meaningful name.
- **In a data row:** a value spanning columns genuinely applies to all of them (e.g. `Standard` across all variants), so the repeat is kept.

**Vertical merge (`vMerge`).** One cell spans several rows, for example a `Category` cell covering five feature rows. Word stores the text only in the first cell, and the cells below are empty continuations. I **forward-fill**: a `vMerge` continuation cell takes the value from the cell above.

```python
prev_row = None
for row in table.rows:
    cells = [c.text.strip() for c in row.cells]
    for i, c in enumerate(row.cells):
        vm = c._tc.tcPr.vMerge if c._tc.tcPr is not None else None
        if vm is not None and vm.val != "restart" and prev_row:
            cells[i] = prev_row[i]          # forward-fill vertical merge
    rows.append(cells)
    prev_row = cells
```

**Why it matters:** each row becomes its own chunk. Without forward-fill, a row sentence reads `Category = ; Feature = ABS`, which loses the context. With it, the sentence reads `Category = Safety; Feature = ABS`, and it can be retrieved on its own.

### 8.3 How did you identify section headers and sub-headers: XML parsing or font info?

**XML styles first, font information only as a fallback.**

**Primary: paragraph styles in the XML.**
- Every docx paragraph has a style (`<w:pStyle w:val="Heading2"/>`). I read `paragraph.style.name`: `Heading 1` is a section, `Heading 2` and `Heading 3` are sub-sections, and the number gives the level. This is exact and doesn't depend on how the text looks.
- I keep a **heading stack**, so every chunk carries the full path, like `Braking System > ABS > Warning Indicators`, not just the nearest heading.
- I also check the style's **outline level** (`w:outlineLvl`), because company templates often use custom styles like `BRD Section Title` that are still headings structurally.
- Styles like `TOC 1` (table of contents) and `Caption` are explicitly excluded.

**Fallback: font information.** Not every author uses heading styles; some just make `Normal` text bold and larger. If a paragraph has no heading style, it's treated as a heading when:
- every run is bold, or its font size is above the document's most common body size
- the line is short (under about 12 words) with no ending period
- it's followed by normal body text

The level is worked out by ranking the distinct heading font sizes: the largest is level 1, the next is level 2, and so on.

**Why this order:** styles are exact and cheap, while font rules are guesses that can misfire on bold emphasis inside body text. **PDF** has no styles at all, so font size is the only signal there. That's why docx gave much more reliable section structure.

> **One-liner:** "XML styles and outline levels first, because they're exact. Font size and bold only as a fallback for badly formatted documents. For PDF, font information is the only option."
