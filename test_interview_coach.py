"""Quick test of Interview Coach without needing full KB setup."""

from pathlib import Path
from interview_coach import DocumentLoader, RetrievalEngine

# Create temporary test documents
test_docs_dir = Path("/tmp/test_kb_docs")
test_docs_dir.mkdir(exist_ok=True)

# Write sample documents
(test_docs_dir / "kubernetes.txt").write_text("""
Kubernetes is an open-source container orchestration platform.
It automates deployment, scaling, and management of containerized applications.
Key concepts: pods, services, deployments, namespaces.
Kubernetes helps manage distributed systems at scale.
""")

(test_docs_dir / "distributed_systems.txt").write_text("""
Distributed systems consist of multiple autonomous computers that communicate through a network.
Challenges include consistency, availability, and partition tolerance (CAP theorem).
Examples: microservices, database replication, message queues.
Containerization with Docker and Kubernetes is common for distributed systems.
""")

(test_docs_dir / "cloud.txt").write_text("""
Cloud computing provides on-demand computing resources over the internet.
Major providers: AWS, Google Cloud Platform, Microsoft Azure.
Services: IaaS (Infrastructure), PaaS (Platform), SaaS (Software).
Cloud infrastructure enables scalable distributed applications.
""")

# Create test career history
career_file = test_docs_dir / "career.json"
career_file.write_text("""{
  "summary": "Infrastructure engineer with 25+ years experience",
  "skills": ["Kubernetes", "GCP", "Python", "Terraform", "Docker"],
  "experience": [
    {
      "company": "GSK",
      "role": "AI Platform Engineer",
      "duration": "2023-present",
      "achievements": ["Built multi-region deployment pipelines", "Managed Kubernetes clusters"]
    }
  ]
}""")

# Test 1: Load documents
print("=" * 60)
print("TEST 1: Document Loading")
print("=" * 60)

loader = DocumentLoader(test_docs_dir, career_file)
docs = loader.load_all()
print(f"[OK] Loaded {len(docs)} documents")
for doc in docs:
    print(f"  - {doc.source} ({len(doc.content)} chars)")

# Test 2: Retrieval with BM25 only
print("\n" + "=" * 60)
print("TEST 2: BM25-only Search")
print("=" * 60)

engine_bm25 = RetrievalEngine(docs, "test_profile", use_embeddings=False)
result = engine_bm25.retrieve_for_question("Tell me about containerization")
print(f"Question: {result['question']}")
print(f"Search method: {result['metadata']['search_method']}")
print(f"Search time: {result['metadata']['search_time_ms']}ms")
print(f"Results ({len(result['documents'])}):")
for i, doc in enumerate(result['documents'], 1):
    print(f"  {i}. {Path(doc['source']).name} (score: {doc['score']})")
    print(f"     Preview: {doc['content'][:80]}...")

# Test 3: Retrieval with embeddings (if available)
print("\n" + "=" * 60)
print("TEST 3: Hybrid BM25 + Embeddings Search")
print("=" * 60)

try:
    import time
    init_start = time.time()
    engine_hybrid = RetrievalEngine(docs, "test_profile", use_embeddings=True)
    init_time = (time.time() - init_start) * 1000
    print(f"[Initialization time: {init_time:.2f}ms (one-time: loads model + embeds docs)]")

    result = engine_hybrid.retrieve_for_question("Tell me about containerization")
    print(f"Question: {result['question']}")
    print(f"Search method: {result['metadata']['search_method']}")
    print(f"Search time: {result['metadata']['search_time_ms']}ms")
    print(f"Results ({len(result['documents'])}):")
    for i, doc in enumerate(result['documents'], 1):
        print(f"  {i}. {Path(doc['source']).name} (score: {doc['score']})")
        print(f"     Preview: {doc['content'][:80]}...")
except ImportError as e:
    print(f"[WARN] Embeddings not available (install sentence-transformers to test)")
    print(f"  Error: {e}")

# Test 4: Different questions
print("\n" + "=" * 60)
print("TEST 4: Multiple Questions")
print("=" * 60)

questions = [
    "What's a good example of distributed systems from your experience?",
    "How do you handle cloud infrastructure?",
    "Tell me about your Kubernetes expertise"
]

for q in questions:
    result = engine_bm25.retrieve_for_question(q)
    top_doc = result['documents'][0] if result['documents'] else None
    print(f"Q: {q}")
    if top_doc:
        print(f"   -> {Path(top_doc['source']).name} (score: {top_doc['score']})")
    print()

print("=" * 60)
print("[OK] All tests completed!")
print("=" * 60)
