# Code walkthrough

A plain-language guide for explaining this project in an interview.

## The flow

1. **Chunk** (`rag/chunker.py`): cut each document into small passages at its headings.
2. **Index** (`rag/index.py` + `rag/bm25.py`): prepare to score passages against any question.
3. **Retrieve**: score every passage for the question and keep the top 3.
4. **Answer** (`rag/generate.py`): pick the best sentence, or ask Claude to answer from the 3 passages with citations.
5. **Evaluate** (`rag/evaluate.py`): check, for 22 known questions, whether the right passage comes back.

## `chunker.py`

It reads a Markdown file line by line. When it meets a heading (`#`, `##`, …) it closes the current passage and updates the **heading path**, e.g. `Architecture > 5. ADRs > ADR-003: NAT gateway`. Every passage carries that path, which makes citations readable. Diagram code (```mermaid) is skipped, because it's drawing instructions, not text. Sections longer than ~180 words are split at paragraph breaks.

## `bm25.py`: how the ranking works

**BM25** is the classic search-engine formula. For each word in the question it asks three things:
1. **Does the passage contain the word?** Repeats count more, but with diminishing returns: 10 mentions isn't 10× better than one.
2. **How rare is the word?** That's **IDF**. "liquidation" appears in few passages, so it's a strong clue. "architecture" appears everywhere, so it's a weak one.
3. **How long is the passage?** Long passages match more words by chance, so they're penalized slightly.

`tokenize()` lowercases the text, keeps letters and digits, and drops very common words ("the", "is", "what").

## `generate.py`

- **Extractive mode (default, no AI):** split the top passages into sentences and score each by the rare question words it contains, weighted by how well its passage ranked. Return the best sentence and its source.
- **Claude mode (`--llm`):** each passage goes to the API as a **document block with citations enabled**. The system prompt says *answer only from the documents; if they don't contain the answer, say so*. The response contains text blocks whose `citations` name the passage each claim came from, and the code prints those titles. It also handles a safety **refusal** (`stop_reason == "refusal"`) and enables **server-side fallback**, so a declined request is retried on a suitable model.

## `evaluate.py`: measuring quality

For each test question, the expected answer is a document plus a section name. The metrics:
- **hit@1:** was the right section the *first* result? (0.93)
- **hit@3:** was it in the top 3 passages that get passed on? (1.00)
- **MRR (mean reciprocal rank):** first place scores 1, second ½, third ⅓, averaged (0.96).

It also reports the top score for **unanswerable** questions, which is how the "not found" threshold was set (ADR-004).

## Likely interview questions

- **"Why not just ask the model directly?"** It can invent or misremember. RAG ties every answer to a passage you can check, and the documents can be updated without retraining anything.
- **"Why BM25 and not embeddings?"** It's a strong, free, explainable baseline. Embeddings catch paraphrases, and the production design combines both (hybrid search, ADR-001).
- **"How do you know it works?"** The retrieval evaluation runs in CI on every change. I'd also tell them the eval set is small and needs real user questions.
- **"How do you stop it answering things that aren't in the documents?"** Two layers: a score threshold, which catches some cases and has a measured limitation, and a grounding instruction with citations, which makes unsupported claims visible.
- **"What about prompt injection?"** Documents are passed as data blocks, not instructions, and the corpus is curated public material (risk R-02).
