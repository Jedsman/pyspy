# Prompt and Screenshot Routing Architecture

## Current System (Gemini-only)

### Pathways in Use

#### Pathway 1: Text Prompt Analysis
```
User clicks "Prep for Behavioral Question" (action='copy')
    ↓
custom_prompts.js: handlePromptClick()
    ↓
overlay.html: WebSocket.send({type: 'analyze_text_prompt', prompt: '...'})
    ↓
web_server.py: websocket_endpoint receives message
    ↓
Writes to .command file with analyze_text_prompt command
    ↓
voice_to_code.py: process_commands() reads .command
    ↓
analyze_text_with_gemini(prompt)
    ↓
Results displayed in coach_suggestions panel via WebSocket broadcast
```

#### Pathway 2: Screenshot Analysis (with Gemini)
```
User clicks "Explain This Code" (action='capture')
    ↓
custom_prompts.js: handlePromptClick()
    ↓
Stores prompt in sessionStorage['analysisPrompt']
    ↓
Calls window.electronAPI.startScreenshot()
    ↓
Electron shows screenshot tool
    ↓
User captures region
    ↓
overlay.html receives screenshot in sessionStorage callback
    ↓
Gets analysisPrompt from sessionStorage
    ↓
Calls window.electronAPI.saveScreenshotData(dataUrl) [NO PROMPT PASSED]
    ↓
main.js: save-screenshot-data handler saves PNG file
    ↓
overlay.html: WebSocket.send({type: 'analyze_screenshot', prompt: '...', fileName: 'capture-XXX.png'})
    ↓
web_server.py: websocket_endpoint receives message
    ↓
Writes to .command file with analyze_screenshot command
    ↓
voice_to_code.py: analyze_screenshot_with_gemini_cli(prompt, image_path)
    ↓
Uses Gemini API to analyze image
    ↓
Results displayed in coach_suggestions panel via WebSocket broadcast
```

#### Pathway 3: Code Generation from Transcript
```
User clicks "Generate New Code" (action='new_code')
    ↓
custom_prompts.js: handlePromptClick()
    ↓
User selects transcript segments (checkboxes)
    ↓
Calls triggerCodeGenerationWithTranscripts('new_code', prompt)
    ↓
overlay.html: WebSocket.send({type: 'code_generation_request', action: 'new_code', prompt: '...', transcripts: '...'})
    ↓
web_server.py: Writes code_generation_request to .command file
    ↓
voice_to_code.py: Processes command, calls CodeGenerator
    ↓
CodeGenerator.process_request() → LLM Router (Gemini)
    ↓
Gemini generates code
    ↓
Code written to generated_code/ directory
    ↓
File watcher detects changes, broadcasts via WebSocket
    ↓
Electron receives update, displays in editor
```

---

## Required Dual-Mode Architecture (Gemini + Claude Desktop)

### Design Goals
1. **Screenshot + Prompt** can go to BOTH Gemini (immediate display) and Claude (MCP queue)
2. **Text Prompt** can go to BOTH Gemini (immediate display) and Claude (via MCP)
3. **Code Generation** uses Gemini LLM Router (can be extended to Claude API later)
4. **User can select**: Gemini only, Claude only, or Both

### Required Changes

#### 1. Store prompt alongside screenshot file
**Current**: `saveScreenshotData(dataUrl)` only saves PNG
**Change**: `saveScreenshotData(dataUrl, promptText)` saves:
- `capture-2025-12-03T22-31-45Z.png` (screenshot)
- `capture-2025-12-03T22-31-45Z.txt` (prompt in plain text)

**Files to modify**:
- `overlay.html` - Pass promptText to saveScreenshotData()
- `preload.js` - Update IPC handler signature
- `main.js` - Accept and save promptText alongside screenshot

#### 2. Write prompt queue for Claude Desktop MCP
**Current**: MCP server looks for `.prompt_queue.json` but nothing writes to it
**Change**: After saving screenshot + prompt text file, write to `.prompt_queue.json`:
```json
[
  {
    "filename": "capture-2025-12-03T22-31-45Z.png",
    "prompt": "I am in a coding interview. Use the provided screenshot to analyze the code shown...",
    "timestamp": "2025-12-03T22:31:45Z",
    "type": "screenshot"
  }
]
```

**Files to modify**:
- `main.js` - Write .prompt_queue.json in save-screenshot-data handler

#### 3. Add destination selection to Electron UI
**New control**: Toggle/checkboxes for:
- ☐ Send to Gemini (immediate analysis)
- ☐ Send to Claude Desktop (MCP queue)

**Files to modify**:
- `overlay.html` - Add destination selector UI
- `custom_prompts.js` - Read destination preference, route accordingly

#### 4. Text-only prompts to Claude Desktop
**Current**: Text prompts only go to Gemini (via analyze_text_prompt)
**Change**: Add support for adhoc prompts to MCP queue:

File to modify:
- `main.js` - Add IPC handler for adhoc prompts → `.prompt_queue.json`
- `custom_prompts.js` - For prompts with action='copy', option to also send to Claude

#### 5. Voice-to-Code pathway stays Gemini only
**No change**: Code generation (new_code, update_code) stays with Gemini LLM Router
- User selects transcript
- Clicks "Generate New Code"
- Goes to Gemini via existing pipeline
- Claude can review output via MCP if needed

---

## Alignment Strategy: File-Based Communication

**Key insight**: Both Gemini and Claude use the same **file-watching pattern**.

- **Gemini**: voice_to_code.py watches `.command` file → processes via LLM router
- **Claude Desktop**: MCP server watches `.prompt_queue.json` → reads via check_prompt_queue tool

Both can be triggered by the same Electron action. No complex branching needed—just write to multiple queues simultaneously.

---

## Implementation Breakdown

### Phase 1A: Screenshot + Prompt File Storage (PRIORITY)

For prompts with `action: 'capture'` (8 prompts like "Explain This Code", "Find Bugs", etc):

1. **overlay.html** (line ~1942):
   - Pass `analysisPrompt` to `saveScreenshotData(dataUrl, analysisPrompt)`

2. **preload.js**:
   - Update IPC invoke to accept and forward prompt parameter

3. **main.js** (line ~254, save-screenshot-data handler):
   - Accept `promptText` parameter
   - Save `capture-XXX.png` (screenshot)
   - Save `capture-XXX.txt` (prompt text)
   - Write `.command` file with analyze_screenshot (Gemini) [EXISTING]
   - Write `.prompt_queue.json` with screenshot entry (Claude) [NEW]

4. **Test**:
   - Click "Explain This Code" (action='capture')
   - Verify: PNG + TXT files created
   - Verify: `.command` has analyze_screenshot entry
   - Verify: `.prompt_queue.json` has screenshot entry
   - Verify: Gemini processes normally
   - Verify: .prompt_queue.json ready for Claude

**Result**: Screenshot prompts → PNG + TXT + Both queues

---

### Phase 1B: Text-Only Prompt Routing (PRIORITY)

For prompts with `action: 'copy'` (3 prompts like "Prep for Behavioral Question"):

Currently these go to Gemini via `analyze_text_prompt`. Need to also send to Claude:

1. **custom_prompts.js** (line ~269-283, handlePromptClick 'copy' path):
   - Instead of just WebSocket to Gemini
   - Call new IPC handler: `window.electronAPI.sendAdhocPrompt(fullPrompt)`

2. **preload.js**:
   - Add new IPC invoke: `sendAdhocPrompt(prompt)` → calls main.js handler

3. **main.js**:
   - Add new IPC handler `send-adhoc-prompt`:
     - Write `.command` file with analyze_text_prompt (Gemini) [EXISTING]
     - Append to `.prompt_queue.json` with adhoc entry (Claude) [NEW]
   - Also keep WebSocket message (for immediate Gemini response)

4. **Test**:
   - Click "Prep for Behavioral Question" (action='copy')
   - Verify: `.command` has analyze_text_prompt entry
   - Verify: `.prompt_queue.json` has adhoc text entry
   - Verify: Gemini response still appears immediately in UI
   - Verify: .prompt_queue.json ready for Claude

**Result**: Text prompts → Both queues populated

---

### Phase 2: Add Destination Selector UI (OPTIONAL LATER)

When user wants to choose who receives prompts:

1. **overlay.html**: Add checkbox UI for "Gemini" / "Claude Desktop" / "Both"
2. **custom_prompts.js**: Read destination preference
3. **main.js**: Check flags, conditionally write to each queue
4. **preload.js**: Pass destination to handlers

### Phase 3: Verify Claude Desktop Integration (VERIFICATION)

1. Implement Phase 1A + 1B
2. Start `mcp_server.py`
3. Register MCP server in Claude Desktop
4. Run system with both pathways:
   - Click screenshot prompt → verify Claude gets PNG + prompt
   - Click text prompt → verify Claude gets text prompt
5. Verify both appear in Claude Desktop via `check_prompt_queue` tool

---

## File Structure After Changes

```
generated_code/
├── screenshots/
│   ├── capture-2025-12-03T22-31-45Z.png      (screenshot image)
│   └── capture-2025-12-03T22-31-45Z.txt      (prompt text)
│
└── .prompt_queue.json                         (queue for Claude Desktop)
```

---

## Message Flow (Target State)

### Scenario: User clicks "Explain This Code" with "Both" selected

```
User clicks "Explain This Code" (action='capture', destination='both')
    ↓
screenshot + prompt stored
    ↓
main.js:
  - Saves PNG
  - Saves TXT file
  - Writes .prompt_queue.json
    ↓
[PARALLEL PATHS]
    ├─→ PATH A (Gemini):
    │   overlay.html WebSocket → web_server.py → voice_to_code.py
    │   → analyze_screenshot_with_gemini_cli()
    │   → Results broadcast to UI immediately
    │
    └─→ PATH B (Claude):
        .prompt_queue.json created
        Claude Desktop (with MCP server running)
        → Claude calls check_prompt_queue tool
        → Gets PNG + prompt
        → Claude provides analysis
        → User views in Claude Desktop
```

---

## Notes

- **Plain text files**: TXT files alongside PNGs keep metadata simple and filesystem-visible
- **.prompt_queue.json**: MCP server reads and deletes items as Claude processes them
- **Backwards compatible**: Code generation pathway unchanged
- **Optional**: User can run with Gemini only (ignore Claude controls)
- **Extensible**: Easy to add other backends (Claude API future, other LLMs)

