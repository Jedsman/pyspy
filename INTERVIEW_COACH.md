# Interview Coach MCP System - Implementation Plan

## Project Overview
Build a Model Context Protocol (MCP) server that acts as an interview coach, providing real-time answers to interview questions by retrieving relevant context from domain-specific documents and career history.

**Key Constraints:**
- GTX 1070 GPU (use BM25 first, embeddings optional)
- Sub-200ms response times for real-time coaching
- Claude Desktop integration via MCP
- In-memory, no external databases

---

## Architecture

```
Claude Desktop (User Interface)
    ↓
Interview Coach MCP Server (Python)
    ├── Document Loader (PDFs, text files)
    ├── BM25 Index (in-memory, keyword search)
    ├── Career History Store (structured context)
    └── Retrieval Engine (fast candidate selection)
```

**Data Flow:**
1. User asks interview question in Claude Desktop
2. Claude calls MCP's `retrieve_answer` tool with question
3. MCP searches BM25 index, returns top 5 relevant documents + career context
4. Claude reasons over retrieved context, generates interview answer
5. Response sent back to Claude Desktop in <200ms

---

## Phase 1: Core MCP Server Setup

### 1.1 Project Structure
```
interview-coach-mcp/
├── src/
│   ├── mcp_server.py          # Main MCP server implementation
│   ├── document_loader.py     # PDF/text ingestion
│   ├── bm25_index.py          # BM25 search implementation
│   ├── career_context.py      # Career history management
│   └── retrieval_engine.py    # Orchestrates search
├── knowledge_base/
│   ├── documents/             # Your domain PDFs
│   ├── career_history.json    # Your resume/background as structured data
│   └── domain_context.txt     # Additional domain knowledge
├── config/
│   └── mcp_config.json        # Claude Desktop MCP configuration
├── requirements.txt
├── setup.py
└── README.md
```

### 1.2 Dependencies
```
rank-bm25==0.2.8          # BM25 keyword search
pydantic==2.5.0           # Type validation
pdfplumber==0.10.3        # PDF extraction
json5==0.9.14             # Config parsing
```

### 1.3 Initial MCP Server (mcp_server.py)
**Deliverable:** A working MCP server with basic structure
- Implement MCP protocol handler (uses Claude's mcp library)
- Define `retrieve_answer` tool that takes interview question
- Tool returns structured result: {relevant_documents, career_context, summary}
- Add error handling and logging
- Runs on localhost:9999 (configurable port)

**Testing:** Verify server starts and responds to test requests via curl

---

## Phase 2: Document Ingestion

### 2.1 Document Loader (document_loader.py)
**Deliverable:** Robust document ingestion pipeline
- PDF extraction using pdfplumber (preserves structure, handles multiple pages)
- Text file loading (markdown, .txt)
- Document chunking (500-token chunks with 100-token overlap for context preservation)
- Metadata tracking (source filename, page number, chunk index)
- Handles encoding errors gracefully

**Input:** Documents in `knowledge_base/documents/`
**Output:** List of Document objects with content, metadata, chunk IDs

**Testing:** 
- Load sample PDFs from your domain
- Verify chunks are reasonable size
- Check metadata is preserved

### 2.2 Career History Loader (career_context.py)
**Deliverable:** Structured career context store
- Load `career_history.json` with your background:
  ```json
  {
    "summary": "Infrastructure engineer with 25+ years...",
    "current_role": "AI Platform Contractor at GSK",
    "skills": ["GCP", "Kubernetes", "Python", ...],
    "experience": [
      {
        "company": "GSK",
        "role": "AI Platform Engineer",
        "duration": "2023-present",
        "achievements": [...],
        "technologies": [...]
      }
    ],
    "education": {...}
  }
  ```
- Provide helper functions to retrieve relevant career context by skill/role/company
- Cache in memory at server startup

**Testing:** 
- Parse your actual career history
- Verify all fields accessible
- Test context retrieval by different criteria

---

## Phase 3: BM25 Search Index

### 3.1 BM25 Index Implementation (bm25_index.py)
**Deliverable:** Fast in-memory keyword search
- Build BM25 index from all loaded documents at startup
- Implement search(query, k=5) method:
  - Tokenize query (lowercase, split on whitespace, remove stop words)
  - Score all documents against query
  - Return top-k documents with scores
  - Total execution time: <5ms
- Add query expansion: expand domain-specific abbreviations before search

**Query Expansion Examples:**
- "ML" → "machine learning" 
- "DS" → "data science"
- "IaC" → "infrastructure as code"
- (Define domain-specific ones for your interview domain)

**Testing:**
- Time search operations (should be <5ms)
- Test with example interview questions from your domain
- Verify top results are relevant

---

## Phase 4: Retrieval Engine

### 4.1 Retrieval Orchestration (retrieval_engine.py)
**Deliverable:** Unified retrieval combining documents + career context
- Implement `retrieve_for_question(question: str)` method:
  1. Extract keywords from question (NLP-lite: question words, domain terms)
  2. Search BM25 index → top 5 documents
  3. Extract relevant career context (match keywords to skills/experience)
  4. Format response: {documents: [...], career_context: {...}, metadata: {...}}
- Add result formatting for Claude consumption
- Implement confidence scoring (how well documents matched)

**Response Format:**
```python
{
  "question": "How do you handle distributed systems?",
  "documents": [
    {
      "content": "...",
      "source": "kubernetes_guide.pdf",
      "score": 0.87,
      "chunk_id": "doc_5_chunk_12"
    },
    ...
  ],
  "career_context": {
    "relevant_role": "AI Platform Engineer at GSK",
    "relevant_skills": ["Kubernetes", "GCP", "Infrastructure"],
    "relevant_achievement": "Built multi-region deployment pipelines"
  },
  "summary": "Found 5 relevant documents about distributed systems, matched to your Kubernetes and GCP experience at GSK"
}
```

**Testing:**
- Run with real interview questions
- Verify response time <200ms total
- Check that documents + career context are relevant

---

## Phase 5: MCP Tool Integration

### 5.1 MCP Tool Definition (mcp_server.py)
**Deliverable:** Properly defined MCP tools for Claude Desktop
- Define `retrieve_answer` tool:
  - Input: `question` (string)
  - Returns: structured JSON with documents, career context, metadata
- Add `list_knowledge_base` tool (for debugging):
  - Returns list of loaded documents, document count, index stats
- Implement tool error handling with helpful error messages
- Add request/response logging

**Tool Schema Example:**
```python
{
  "name": "retrieve_answer",
  "description": "Retrieve relevant context for an interview question from your domain documents and career history",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "The interview question to find context for"
      }
    },
    "required": ["question"]
  }
}
```

**Testing:**
- Call tools from Claude Desktop
- Verify responses format correctly
- Check error handling with malformed inputs

---

## Phase 6: Claude Desktop Configuration

### 6.1 MCP Configuration (config/mcp_config.json)
**Deliverable:** Ready-to-use Claude Desktop MCP config
- Create `~/Library/Application Support/Claude/claude_desktop_config.json` entry:
  ```json
  {
    "mcpServers": {
      "interview-coach": {
        "command": "python",
        "args": ["/path/to/interview-coach-mcp/src/mcp_server.py"],
        "env": {
          "KNOWLEDGE_BASE_PATH": "/path/to/interview-coach-mcp/knowledge_base"
        }
      }
    }
  }
  ```
- Document manual setup steps
- Add troubleshooting guide (server not starting, tools not visible, etc.)

**Testing:**
- Restart Claude Desktop
- Verify interview-coach tools appear in tool list
- Test calling tools from Claude

---

## Phase 7: Knowledge Base Setup

### 7.1 User Preparation
**Deliverable:** Guide for populating knowledge base
- Create template `career_history.json` with your actual data
- Collect domain-specific PDFs (interview prep guides, technical docs, etc.)
- Create optional `domain_context.txt` with:
  - Key terminology definitions
  - Common patterns in your domain
  - Interview question types for your field
- Document file organization requirements

**Directory Structure to Create:**
```
knowledge_base/
├── career_history.json         # Your background
├── documents/
│   ├── system_design_guide.pdf
│   ├── devops_concepts.pdf
│   └── your_domain_docs.pdf
└── domain_context.txt
```

---

## Phase 8: Testing & Optimization

### 8.1 Functional Testing
**Test Cases:**
- Load documents: Verify all PDFs parse correctly
- Search performance: 10 random questions, measure response times
- Relevance: Run 5-10 real interview questions, manually check results
- Edge cases: Empty question, very long question, domain-specific jargon
- Error handling: Missing files, malformed JSON, search timeouts

### 8.2 Performance Tuning (If Needed)
- If BM25 is too slow: Implement result caching for common questions
- If results aren't relevant: Adjust BM25 parameters (k1, b)
- If career context is missing: Expand keyword matching

### 8.3 Optional: Embedding Reranking (Phase 2+)
- If BM25 results miss semantic matches, add optional Ollama integration:
  - Load `nomic-embed-text` on startup (if available)
  - Rerank BM25 top-30 candidates using embeddings
  - Only if GTX 1070 can handle it (<200ms total)

---

## Phase 9: Documentation & Deployment

### 9.1 User Documentation
- README with setup instructions
- How to populate knowledge base
- Example interview questions and expected answers
- Troubleshooting guide
- Performance tips

### 9.2 Code Documentation
- Docstrings for all functions
- Type hints throughout
- Comments for non-obvious logic

---

## Implementation Order (Recommended)

**Week 1:**
1. Phase 1: Set up MCP server skeleton
2. Phase 2: Document loader + PDF extraction
3. Phase 3: BM25 index implementation

**Week 2:**
4. Phase 4: Retrieval engine orchestration
5. Phase 5: MCP tool integration
6. Phase 7: Populate your knowledge base

**Week 3:**
7. Phase 6: Claude Desktop configuration
8. Phase 8: Testing & optimization
9. Phase 9: Documentation

---

## File Checklist

- [ ] `src/mcp_server.py` - Main MCP server
- [ ] `src/document_loader.py` - PDF/text ingestion
- [ ] `src/bm25_index.py` - Search index
- [ ] `src/career_context.py` - Career history management
- [ ] `src/retrieval_engine.py` - Retrieval orchestration
- [ ] `requirements.txt` - Python dependencies
- [ ] `setup.py` - Package installation
- [ ] `config/mcp_config.json` - Claude Desktop config
- [ ] `knowledge_base/career_history.json` - Your background
- [ ] `knowledge_base/documents/` - Domain PDFs
- [ ] `README.md` - Setup & usage guide
- [ ] `tests/test_retrieval.py` - Test suite (optional but recommended)

---

## Quick Start (After Implementation)

```bash
# 1. Install dependencies
cd interview-coach-mcp
pip install -r requirements.txt

# 2. Populate knowledge base (add your docs and career history)
# Add PDFs to knowledge_base/documents/
# Create knowledge_base/career_history.json

# 3. Configure Claude Desktop
# Copy mcp_config.json entry to ~/.config/Claude/claude_desktop_config.json
# (Mac: ~/Library/Application Support/Claude/claude_desktop_config.json)

# 4. Start Claude Desktop, test tools in sidebar

# 5. Ask interview questions, get instant answers with context
```

---

## Success Criteria

✓ MCP server starts without errors
✓ Documents load and parse correctly
✓ Search responds in <5ms
✓ Full retrieval completes in <200ms
✓ Claude Desktop recognizes tools
✓ Interview questions return relevant context
✓ Career history integrated into answers
✓ Ready to use in real interviews

---

## Notes for Claude Code Execution

This plan is designed to be executed incrementally with Claude Code:

1. **Request creation of each file** with the phase number (e.g., "Phase 2.1: Create document_loader.py")
2. **Test each component** before moving to the next
3. **Use Claude Code's file execution** to test imports and basic functionality
4. **Iterate on BM25 tuning** based on actual interview questions
5. **Optional:** Add embedding support later if needed

Each phase has clear deliverables and testing criteria—use these as checkpoints with Claude Code.