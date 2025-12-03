# Testing Checklist - Stages 1-6 Complete

**Date**: 2025-12-03
**Status**: Ready to test application startup

## Pre-Testing Setup

### 1. Commit Stages 1-6
```bash
# Add modified files
git add config.py claude_desktop_config.json mcp_server.py voice_to_code.py llm_router.py gemini_mcp_client.py

# Delete test files
git rm test_loopback.py test_wasapi_loopback.py test_websocket.py

# Commit
git commit -m "Stages 1-6: Merge Claude Desktop integration with LLM router

- Stage 1: Claude Desktop configuration (config.py, claude_desktop_config.json)
- Stage 2: Enhanced MCP server (view_screenshot, check_prompt_queue tools)
- Stage 3: Verified WASAPI audio capture robustness
- Stage 4: LLM router pattern (llm_router.py for Gemini/Claude/future)
- Stage 5: Dependencies already include both Gemini and Claude
- Stage 6: Cleanup test files and deprecate gemini_mcp_client.py"
```

### 2. Update Dependencies
```bash
uv sync
```

## Quick Startup Test

### Test 1: Python Import Check
```bash
python -c "
from config import GENERATED_CODE_DIR, SCREENSHOTS_DIR
from llm_router import get_router, LLMRouter
from mcp_server import server
print('✅ All imports successful')
"
```

**Expected**: Should print "✅ All imports successful"

### Test 2: Application Startup
```bash
# Make sure you have GOOGLE_API_KEY set
python voice_to_code.py
```

**Expected**:
- Prints initialization messages
- Shows "Using [model] with Function Calling"
- Shows "LLM Router: Gemini"
- Ready to listen for audio

**How to exit**: `Ctrl+C`

### Test 3: MCP Server Startup
```bash
python mcp_server.py
```

**Expected**:
- Server initializes
- Listens on stdio
- No errors

**How to exit**: `Ctrl+C`

## Verification Points

- [ ] Config paths resolve correctly
- [ ] LLM router initializes with Gemini
- [ ] MCP server has 5 tools (capture_transcript, capture_screenshot, get_interview_context, view_screenshot, check_prompt_queue)
- [ ] Custom prompts still supported
- [ ] No import errors
- [ ] No deprecation warnings (except for gemini_mcp_client.py)
- [ ] Audio capture device detection works

## Next Stages (When Ready)

### Stage 7: Claude Desktop Integration
- Add environment variable for LLM selection
- Create Claude Desktop mode detection
- Test MCP server with Claude Desktop

### Stage 8: Full Integration Testing
- Complete voice-to-code flow
- Test code generation
- Verify no memory leaks
- Check performance

---

**Ready?** Run the tests above and let me know the results!
