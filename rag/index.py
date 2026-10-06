"""Build a searchable index from a folder of .md / .txt files."""

from pathlib import Path

from .bm25 import BM25, tokenize
from .chunker import split_markdown

DEFAULT_CORPUS = Path(__file__).resolve().parent.parent / "corpus"


class Index:
    def __init__(self, chunks):
        self.chunks = chunks
        # The heading is indexed together with the text, so "ADR-003: NAT gateway" helps matching.
        self.bm25 = BM25([tokenize(c["heading"] + " " + c["text"]) for c in chunks])

    @classmethod
    def from_folder(cls, folder=DEFAULT_CORPUS, max_words=180):
        chunks = []
        for path in sorted(Path(folder).glob("*")):
            if path.suffix.lower() in (".md", ".txt"):
                chunks += split_markdown(path.read_text(encoding="utf-8"), path.stem, max_words)
        if not chunks:
            raise ValueError(f"no .md or .txt documents found in {folder}")
        return cls(chunks)

    def search(self, question, k=3):
        """Return the k best chunks, each with its BM25 score added."""
        return [dict(self.chunks[i], score=round(s, 3))
                for i, s in self.bm25.search(tokenize(question), k)]
