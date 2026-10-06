# RAG Assistant over Public Documents

![tests](https://github.com/aadirani/rag-public-docs-assistant/actions/workflows/tests.yml/badge.svg)

Ask questions about a set of documents and get answers **with the source section cited**. When the answer isn't in the documents, the assistant should say so instead of making something up.

## The idea in one paragraph

AI models sometimes "remember" things wrongly. **Retrieval-Augmented Generation (RAG)** fixes that by working like an open-book exam: first **find** the most relevant passages in your own documents, then **answer only from those passages** and show where each claim came from. This project builds the "find" part from scratch, **measures how well it works**, and can optionally hand the passages to Claude to write the answer, with citations.

## Quick start

Needs Python 3.9+. Nothing to install for the default mode.

```bash
python -m rag ask "Why use a single shared NAT gateway by default?"
python -m rag ask "What is the capital of France?"   # -> I couldn't find this in the documents.
python -m rag eval                                    # retrieval quality report
```

Example output:

```
Retrieved passages:
   17.03  [aws-three-tier-reference > ... > ADR-003: NAT gateway: one shared by default, one per AZ in production]
    9.40  [aws-three-tier-reference > ... > 8. AWS Well-Architected mapping]
    8.70  [aws-three-tier-reference > ... > 6. Risk register]

Best matching sentence: Decision: (b) by default, (a) for production (nat_gateway_per_az = true).
```

**Optional: answers written by Claude, with citations.** This needs the Anthropic SDK and API credentials:

```bash
pip install anthropic
python -m rag ask "Why use a single shared NAT gateway by default?" --llm
```

## Results

| Metric | Score |
|---|---|
| Correct section ranked first (hit@1) | 0.93 |
| Correct section in the top 3 (hit@3) | 1.00 |
| Unanswerable questions caught by the "not found" check | 4 of 7 |

The last line is a real limitation: keyword search alone can't always tell that a question *isn't* answered. [ARCHITECTURE.md](ARCHITECTURE.md#5-architecture-decision-records) explains why (ADR-004) and what would fix it.

## What's inside

| Path | What it is |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design, diagrams, evaluation results, 6 decision records, risks, costs, production design |
| [rag/](rag/) | Chunker, BM25 retriever, answer generation, evaluation, command line |
| [eval/questions.json](eval/questions.json) | 22 test questions (15 answerable, 7 not) |
| [corpus/](corpus/) | Sample documents: this portfolio's own architecture write-ups (swap in any `.md`/`.txt` files) |
| [docs/code-walkthrough.md](docs/code-walkthrough.md) | Plain-language explanation |

## Limitations

- The evaluation set is small and was written alongside the documents. Real user questions would be harder.
- The Claude mode isn't exercised by the automated tests, because it needs API credentials.

---

Built with AI assistance.
