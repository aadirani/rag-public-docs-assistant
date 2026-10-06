import unittest

from rag.bm25 import BM25, tokenize
from rag.chunker import split_markdown
from rag.evaluate import evaluate, is_relevant
from rag.generate import extractive_answer
from rag.index import Index

DOC = """# Title

Intro text.

## Power

The UPS bridges the generator start.

```mermaid
flowchart LR
    A --> B
```

## Backup

### Offline copy

Disks are rotated weekly.
"""


class ChunkerTests(unittest.TestCase):
    def test_heading_path_and_mermaid_skipped(self):
        chunks = split_markdown(DOC, "demo")
        headings = [c["heading"] for c in chunks]
        self.assertIn("Title > Power", headings)
        self.assertIn("Title > Backup > Offline copy", headings)
        self.assertFalse(any("flowchart" in c["text"] for c in chunks))

    def test_long_sections_are_split(self):
        text = "# H\n\n" + "\n\n".join(["word " * 100] * 5)
        chunks = split_markdown(text, "long", max_words=180)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c["text"].split()) <= 200 for c in chunks))


class BM25Tests(unittest.TestCase):
    def test_tokenize_drops_stopwords(self):
        self.assertEqual(tokenize("What is the NAT gateway?"), ["nat", "gateway"])

    def test_ranking(self):
        docs = [tokenize("backup disks rotated weekly"),
                tokenize("generator and ups power"),
                tokenize("ups battery runtime ups sizing")]
        bm = BM25(docs)
        results = bm.search(tokenize("ups battery"), k=3)
        self.assertEqual(results[0][0], 2)            # mentions both words
        self.assertNotIn(0, [i for i, _ in results])  # no matching word -> not returned

    def test_rare_words_weigh_more(self):
        bm = BM25([tokenize("ups ups"), tokenize("ups"), tokenize("ups liquidation")])
        self.assertGreater(bm.idf["liquidation"], bm.idf["ups"])


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = Index.from_folder()

    def test_corpus_loaded(self):
        sources = {c["source"] for c in self.index.chunks}
        self.assertEqual(len(sources), 4)

    def test_known_question_retrieves_right_section(self):
        hits = self.index.search("Why use a single shared NAT gateway by default?", k=3)
        self.assertTrue(any(h["source"] == "aws-three-tier-reference" and "ADR-003" in h["heading"]
                            for h in hits))

    def test_extractive_answer_has_source(self):
        q = "How is the liquidation price of a long position estimated?"
        hits = self.index.search(q, k=3)
        sentence, hit = extractive_answer(q, hits, self.index.bm25.idf)
        self.assertTrue(sentence)
        self.assertEqual(hit["source"], "perp-futures-risk-calculator")

    def test_evaluate_metrics_on_toy_questions(self):
        questions = [
            {"question": "NAT gateway shared by default",
             "expected": [{"source": "aws-three-tier-reference", "heading": "ADR-003"}]},
            {"question": "capital of France", "expected": []},
        ]
        result = evaluate(self.index, questions, k=3)
        self.assertEqual(result["questions"], 1)
        self.assertEqual(result["hit_at_3"], 1.0)

    def test_is_relevant(self):
        chunk = {"source": "a", "heading": "Doc > ADR-001: X"}
        self.assertTrue(is_relevant(chunk, [{"source": "a", "heading": "adr-001"}]))
        self.assertFalse(is_relevant(chunk, [{"source": "b", "heading": "ADR-001"}]))


if __name__ == "__main__":
    unittest.main()
