"""Turn retrieved chunks into an answer.

Two modes:
- extractive (default, no AI model): return the single best-matching sentence, with its source.
- Claude (optional): send the chunks as documents with citations enabled, so every claim
  in the answer points back to a retrieved passage. Needs `pip install anthropic` and
  Anthropic API credentials (e.g. the ANTHROPIC_API_KEY environment variable).
"""

import re

from .bm25 import tokenize

MODEL = "claude-opus-5-5"
SYSTEM = (
    "You answer questions using only the documents provided in the user's message. "
    "If the documents do not contain the answer, say that plainly instead of guessing. "
    "Keep the answer short and factual."
)


def cite(chunk):
    return f"[{chunk['source']} > {chunk['heading']}]"


def extractive_answer(question, hits, idf):
    """Pick the sentence that shares the most (rare) words with the question.

    Each sentence's score is weighted by how well its passage ranked, so a sentence
    from the best passage wins over an equally good one from a weaker passage.
    """
    query = set(tokenize(question))
    best, best_score, best_hit = None, 0.0, None
    top = hits[0]["score"] if hits else 1
    for hit in hits:
        weight = hit["score"] / top
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", hit["text"]):
            words = set(tokenize(sentence))
            score = weight * sum(idf.get(w, 0) for w in query & words)
            if score > best_score:
                best, best_score, best_hit = sentence.strip(" -|*"), score, hit
    if best is None:
        return None, None
    return best, best_hit


def answer_with_claude(question, hits, model=MODEL):
    """Ask Claude to answer from the retrieved chunks only. Returns (answer, cited titles)."""
    import anthropic  # optional dependency, imported only when this mode is used

    client = anthropic.Anthropic()
    documents = [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": h["text"]},
            "title": f"{h['source']} > {h['heading']}",
            "citations": {"enabled": True},
        }
        for h in hits
    ]
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        # If a safety classifier declines, the API retries on a suitable fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        # Short look-up answers don't need deep reasoning; low effort keeps cost down.
        output_config={"effort": "low"},
        system=SYSTEM,
        messages=[{"role": "user", "content": documents + [{"type": "text", "text": question}]}],
    )
    if response.stop_reason == "refusal":
        return "The model declined to answer this question.", []

    text, titles = [], set()
    for block in response.content:
        if block.type == "text":
            text.append(block.text)
            for citation in block.citations or []:
                titles.add(citation.document_title)
    return "".join(text).strip(), sorted(titles)
