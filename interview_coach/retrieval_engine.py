"""Orchestrate document retrieval for interview questions."""

import time
import json
from typing import Dict, Any, Optional
from .bm25_index import BM25Index
from .embedding_index import EmbeddingIndex


class RetrievalEngine:
    """Retrieve relevant context with hybrid BM25 + semantic search."""

    def __init__(self, documents, kb_profile_name: str, use_embeddings: bool = True):
        self.documents = documents
        self.bm25 = BM25Index(documents)
        self.profile_name = kb_profile_name
        self.embedding_index = None
        self.use_embeddings = use_embeddings

        # Optional: build embedding index for semantic reranking
        if use_embeddings:
            try:
                self.embedding_index = EmbeddingIndex()
                self.embedding_index.build_index(documents)
            except Exception as e:
                print(f"Warning: Could not initialize embeddings: {e}")
                self.embedding_index = None

    def retrieve_for_question(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """Get relevant documents using hybrid BM25 + embeddings."""
        start_time = time.time()

        # BM25 search (fast, gets top 20 candidates)
        bm25_results = self.bm25.search(question, k=max(20, top_k * 4))

        # Optional: rerank with embeddings for semantic relevance
        if self.embedding_index and self.use_embeddings:
            final_results = self.embedding_index.rerank(question, bm25_results, k=top_k)
        else:
            final_results = bm25_results[:top_k]

        # Format response
        documents = []
        for doc, score in final_results:
            documents.append({
                "content": doc.content[:500],  # Preview only
                "source": doc.source,
                "score": round(float(score), 2),
                "doc_type": doc.doc_type
            })

        search_time_ms = (time.time() - start_time) * 1000

        return {
            "question": question,
            "documents": documents,
            "metadata": {
                "search_time_ms": round(search_time_ms, 2),
                "profile": self.profile_name,
                "document_count": len(documents),
                "search_method": "hybrid (BM25 + embeddings)" if self.embedding_index else "BM25 only"
            }
        }
