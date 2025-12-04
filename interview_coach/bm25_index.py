"""BM25 search index for fast document retrieval."""

from typing import List, Dict, Tuple
import re


class BM25Index:
    """Simple BM25 implementation for fast keyword search."""

    def __init__(self, documents):
        self.documents = documents
        self.index = {}
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        # Remove very short words
        return [w for w in words if len(w) > 2]

    def _build_index(self):
        """Build inverted index."""
        for doc_idx, doc in enumerate(self.documents):
            tokens = self._tokenize(doc.content)
            for token in set(tokens):  # unique tokens per doc
                if token not in self.index:
                    self.index[token] = []
                self.index[token].append(doc_idx)

    def search(self, query: str, k: int = 5) -> List[Tuple]:
        """Search for relevant documents. Returns list of (doc, score)."""
        tokens = self._tokenize(query)
        if not tokens:
            return []

        # Score documents by token matches
        scores = {}
        for token in tokens:
            if token in self.index:
                for doc_idx in self.index[token]:
                    scores[doc_idx] = scores.get(doc_idx, 0) + 1

        # Sort by score, return top k with documents
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [(self.documents[doc_idx], score / len(tokens)) for doc_idx, score in ranked]
