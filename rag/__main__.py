"""Command line:
  python -m rag ask "Why use a single NAT gateway?"          (retrieval + extractive answer)
  python -m rag ask "Why use a single NAT gateway?" --llm    (retrieval + Claude, with citations)
  python -m rag eval                                         (retrieval quality metrics)
"""

import argparse
import sys

from . import evaluate as ev
from .generate import answer_with_claude, cite, extractive_answer
from .index import DEFAULT_CORPUS, Index

# Below this BM25 score the best match is too weak: say "not found" rather than guess.
# Calibrated on eval/questions.json (see the eval output and ARCHITECTURE.md).
MIN_SCORE = 6.0


def ask(args):
    index = Index.from_folder(args.corpus)
    hits = index.search(args.question, args.k)
    if not hits or hits[0]["score"] < args.min_score:
        print("I couldn't find this in the documents.")
        return

    print("Retrieved passages:")
    for h in hits:
        print(f"  {h['score']:>6.2f}  {cite(h)}")
    print()

    if args.llm:
        try:
            import anthropic
        except ImportError:
            sys.exit("Claude mode needs the SDK: pip install anthropic")
        try:
            answer, titles = answer_with_claude(args.question, hits)
        except anthropic.AuthenticationError:
            sys.exit("No valid Anthropic credentials. Set ANTHROPIC_API_KEY and try again.")
        except anthropic.RateLimitError:
            sys.exit("Rate limited by the API. Wait a moment and try again.")
        except anthropic.APIStatusError as err:
            sys.exit(f"API error {err.status_code}: {err.message}")
        except anthropic.APIConnectionError:
            sys.exit("Could not reach the API. Check the internet connection.")
        print(answer)
        if titles:
            print("\nCited: " + "; ".join(titles))
    else:
        sentence, hit = extractive_answer(args.question, hits, index.bm25.idf)
        print(f"Best matching sentence: {sentence}\nSource: {cite(hit)}")


def run_eval(args):
    index = Index.from_folder(args.corpus)
    result = ev.evaluate(index, ev.load_questions(args.questions), args.k)
    print(f"{'rank':>4}  {'top':>6}  question")
    for r in result["rows"]:
        rank = "-" if r["rank"] is None else str(r["rank"])
        label = "" if r["answerable"] else "   (should NOT be answered)"
        print(f"{rank:>4}  {r['top_score']:>6.2f}  {r['question']}{label}")
    k = args.k
    print(f"\nanswerable questions: {result['questions']}")
    print(f"hit@1: {result['hit_at_1']:.2f}   hit@{k}: {result[f'hit_at_{k}']:.2f}   MRR: {result['mrr']:.2f}")
    print(f"lowest top score (answerable):    {result['min_top_score_answerable']:.2f}")
    print(f"highest top score (unanswerable): {result['max_top_score_unanswerable']:.2f}")
    print(f"'not found' threshold:            {MIN_SCORE:.2f}")

    if result[f"hit_at_{k}"] < args.min_hit:
        sys.exit(f"FAIL: hit@{k} {result[f'hit_at_{k}']:.2f} is below the required {args.min_hit:.2f}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="rag", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("ask", help="answer a question from the documents")
    a.add_argument("question")
    a.add_argument("--k", type=int, default=3, help="number of passages to retrieve")
    a.add_argument("--llm", action="store_true", help="generate the answer with Claude")
    a.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    a.add_argument("--min-score", type=float, default=MIN_SCORE)
    a.set_defaults(func=ask)

    e = sub.add_parser("eval", help="measure retrieval quality on eval/questions.json")
    e.add_argument("--k", type=int, default=3)
    e.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    e.add_argument("--questions", default=str(ev.DEFAULT_QUESTIONS))
    e.add_argument("--min-hit", type=float, default=0.0, help="fail if hit@k is below this")
    e.set_defaults(func=run_eval)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
