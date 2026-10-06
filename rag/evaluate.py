"""Retrieval evaluation: does the right passage come back for each test question?"""

import json
from pathlib import Path

DEFAULT_QUESTIONS = Path(__file__).resolve().parent.parent / "eval" / "questions.json"


def is_relevant(chunk, expected):
    """A chunk is relevant if it comes from an expected document and section."""
    return any(chunk["source"] == e["source"] and e["heading"].lower() in chunk["heading"].lower()
               for e in expected)


def evaluate(index, questions, k=3):
    """Return metrics for answerable questions and top scores for unanswerable ones.

    hit@1 / hit@k: share of questions whose first / top-k results include a relevant chunk.
    MRR: average of 1 / rank of the first relevant chunk (1.0 = always first).
    """
    rows, hits1, hitsk, rr = [], 0, 0, 0.0
    answerable = [q for q in questions if q["expected"]]
    for q in questions:
        results = index.search(q["question"], k)
        top = results[0]["score"] if results else 0.0
        rank = next((i + 1 for i, c in enumerate(results) if is_relevant(c, q["expected"])), None)
        if q["expected"]:
            hits1 += rank == 1
            hitsk += rank is not None
            rr += 1 / rank if rank else 0
        rows.append({"question": q["question"], "answerable": bool(q["expected"]),
                     "rank": rank, "top_score": top})
    n = len(answerable) or 1
    unanswerable_tops = [r["top_score"] for r in rows if not r["answerable"]]
    answerable_tops = [r["top_score"] for r in rows if r["answerable"]]
    return {
        "questions": len(answerable),
        "hit_at_1": hits1 / n,
        f"hit_at_{k}": hitsk / n,
        "mrr": rr / n,
        "min_top_score_answerable": min(answerable_tops) if answerable_tops else None,
        "max_top_score_unanswerable": max(unanswerable_tops) if unanswerable_tops else None,
        "rows": rows,
    }


def load_questions(path=DEFAULT_QUESTIONS):
    return json.loads(Path(path).read_text(encoding="utf-8"))
