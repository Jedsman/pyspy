"""Embedding-based semantic search for document reranking."""

import numpy as np
from typing import List, Tuple


class EmbeddingIndex:
    """Lightweight embedding index using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.embeddings = []
        self.documents = []
        self._load_model()

    def _load_model(self):
        """Load embedding model (lazy loading)."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        except ImportError:
            print(f"Warning: sentence-transformers not available. Install with: pip install sentence-transformers")
            self.model = None

    def build_index(self, documents):
        """Precompute embeddings for all documents."""
        if not self.model:
            return

        self.documents = documents
        texts = [doc.content[:512] for doc in documents]  # Truncate for speed

        try:
            self.embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        except Exception as e:
            print(f"Error building embeddings: {e}")
            self.embeddings = []

    def rerank(self, query: str, candidates: List[Tuple], k: int = 5) -> List[Tuple]:
        """Rerank candidates using semantic similarity.

        Args:
            query: The search query
            candidates: List of (document, bm25_score) tuples from BM25
            k: Number of results to return

        Returns:
            List of (document, combined_score) tuples
        """
        if not self.model or not self.embeddings.any():
            # Fallback: return original BM25 ranking
            return candidates[:k]

        try:
            # Get query embedding
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]

            # Get indices of candidate documents
            candidate_docs = [doc for doc, _ in candidates]
            candidate_indices = [self.documents.index(doc) for doc in candidate_docs if doc in self.documents]

            if not candidate_indices:
                return candidates[:k]

            # Compute cosine similarity for candidates
            candidate_embeddings = self.embeddings[candidate_indices]
            similarities = np.dot(candidate_embeddings, query_embedding) / (
                np.linalg.norm(candidate_embeddings, axis=1) * np.linalg.norm(query_embedding)
            )

            # Combine BM25 and embedding scores (weighted average)
            bm25_scores = [score for _, score in candidates[:len(candidate_indices)]]
            combined_scores = 0.3 * np.array(bm25_scores) + 0.7 * similarities

            # Sort by combined score
            ranked_indices = np.argsort(combined_scores)[::-1][:k]

            return [(candidate_docs[i], float(combined_scores[i])) for i in ranked_indices]

        except Exception as e:
            print(f"Error in reranking: {e}")
            return candidates[:k]
