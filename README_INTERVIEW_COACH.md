# Interview Coach Module

Real-time interview context retrieval integrated into the voice-to-code MCP server.

## Quick Start

### 1. Create Knowledge Base Structure

Create `~/.interview_coach/` directory:

```bash
mkdir -p ~/.interview_coach/profiles/default/{documents}
```

### 2. Configure Knowledge Base

Create `~/.interview_coach/knowledge_base_config.json`:

```json
{
  "active_profile": "default",
  "profiles": {
    "default": {
      "name": "Default Interview Prep",
      "documents_path": "~/.interview_coach/profiles/default/documents",
      "career_history_file": "~/.interview_coach/profiles/default/career_history.json",
      "domain_context_file": "~/.interview_coach/profiles/default/domain_context.txt"
    }
  }
}
```

### 3. Add Career History

Create `~/.interview_coach/profiles/default/career_history.json`:

```json
{
  "summary": "Your professional summary",
  "skills": ["Skill1", "Skill2", "Skill3"],
  "experience": [
    {
      "role": "Your Role",
      "company": "Company Name",
      "duration": "2023-present",
      "achievements": ["Achievement 1", "Achievement 2"],
      "technologies": ["Tech1", "Tech2"]
    }
  ]
}
```

### 4. Add Domain Documents

Put `.txt` or `.md` files in:
```
~/.interview_coach/profiles/default/documents/
```

## Tools

### retrieve_answer
Get relevant context for an interview question.

```python
tool_call("retrieve_answer", {"question": "What's your experience with distributed systems?"})
```

Returns:
```json
{
  "question": "What's your experience with distributed systems?",
  "documents": [
    {
      "content": "...",
      "source": "kubernetes_guide.txt",
      "score": 0.95,
      "doc_type": "text"
    }
  ],
  "metadata": {
    "search_time_ms": 2.5,
    "profile": "default",
    "document_count": 3
  }
}
```

### list_knowledge_bases
List available KB profiles and show active one.

### switch_knowledge_base
Switch to a different KB profile.

```python
tool_call("switch_knowledge_base", {"profile_name": "company_x"})
```

### archive_interview_session
Archive a practice session with question, answer, and sources.

```python
tool_call("archive_interview_session", {
  "question": "...",
  "answer": "...",
  "sources": ["kubernetes_guide.txt"]
})
```

Sessions are saved to `~/.interview_coach/archive/{profile}/YYYY/MM/DD/`

## Multiple Profiles

Add more profiles to `knowledge_base_config.json`:

```json
{
  "active_profile": "default",
  "profiles": {
    "default": {...},
    "company_x": {
      "name": "Company X Prep",
      "documents_path": "~/.interview_coach/profiles/company_x/documents",
      "career_history_file": "~/.interview_coach/profiles/company_x/career_history.json",
      "domain_context_file": "~/.interview_coach/profiles/company_x/domain_context.txt"
    }
  }
}
```

Switch with `switch_knowledge_base` tool.

## Hybrid Search: BM25 + Semantic Embeddings

By default, Interview Coach uses **hybrid search** combining:

1. **BM25 keyword search** (fast, <5ms)
   - Initial retrieval of top 20 candidates
   - Excellent for exact terminology matches

2. **Semantic reranking with embeddings** (<50ms total)
   - Uses lightweight `all-MiniLM-L6-v2` model (~80MB)
   - Understands synonyms and related concepts
   - Better for paraphrased questions
   - Reranks top candidates by semantic similarity

**Search method**: Combined (70% semantic, 30% keyword)

This gives you quality results from day 1, even with a small KB.

### Disabling Embeddings

If you want BM25-only search (faster, no GPU), set environment variable:

```bash
export INTERVIEW_COACH_USE_EMBEDDINGS=false
```

Or pass `use_embeddings=False` when initializing RetrievalEngine.

---

## Supported Document Formats

By default, the loader supports:
- `.txt` - Plain text files
- `.md` - Markdown files
- `.html` - HTML files (text extracted)
- `.pdf` - PDF files (requires `pdfplumber` or `PyPDF2`)
- `.docx` - Word documents (requires `python-docx`)

### Optional Dependencies

Install to enable additional features:

```bash
# For semantic search with embeddings (recommended)
pip install sentence-transformers

# For PDF support
pip install pdfplumber
# or
pip install PyPDF2

# For DOCX support
pip install python-docx
```

**First install**: `sentence-transformers` will download `all-MiniLM-L6-v2` model (~80MB) on first use.

### Custom Format Support

Pass custom format mappings to DocumentLoader:

```python
from pathlib import Path
from interview_coach import DocumentLoader

custom_formats = {
    "txt": "plain_text",
    "pdf": "pdf",
    "custom": "plain_text",  # treat .custom as plain text
}

loader = DocumentLoader(
    documents_path=Path("./docs"),
    career_history_file=Path("./career.json"),
    supported_formats=custom_formats
)
docs = loader.load_all()
```

## Environment Variable

Override base path with `INTERVIEW_COACH_BASE_PATH`:

```bash
export INTERVIEW_COACH_BASE_PATH=/custom/path
```

## Future Enhancements

- Learning engine: Analyze archived sessions to identify KB gaps
- Embedding-based reranking for semantic search
- Integration with voice transcripts for automatic archiving
