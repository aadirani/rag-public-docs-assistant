"""BM25: the classic keyword-ranking formula used by search engines (pure Python)."""

import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = set("""
a an and are as at be but by can do does for from has have how i if in into is it its
of on or so than that the their then there these this to was what when where which who
why will with you your we our not no yes should would could my me
""".split())


def tokenize(text):
    return [t for t in TOKEN.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]


class BM25:
    """Score documents for a query.

    For each query word: rarer words count more (IDF), repeated words count more but
    with diminishing returns (k1), and long documents are penalised a little (b).
    """

    def __init__(self, documents, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(doc) for doc in documents]
        self.lengths = [len(doc) for doc in documents]
        self.avg_len = sum(self.lengths) / len(documents) if documents else 0
        n = len(documents)
        df = Counter(term for doc in documents for term in set(doc))
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query_terms, i):
        tf, length = self.tf[i], self.lengths[i]
        total = 0.0
        for term in set(query_terms):
            if term not in tf:
                continue
            f = tf[term]
            norm = f + self.k1 * (1 - self.b + self.b * length / self.avg_len)
            total += self.idf[term] * f * (self.k1 + 1) / norm
        return total

    def search(self, query_terms, k=3):
        """Return [(index, score), ...] best first, skipping documents with no matching word."""
        scored = [(i, self.score(query_terms, i)) for i in range(len(self.tf))]
        scored = [s for s in scored if s[1] > 0]
        return sorted(scored, key=lambda s: s[1], reverse=True)[:k]
