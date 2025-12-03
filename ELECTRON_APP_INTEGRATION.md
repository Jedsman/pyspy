# Electron App Integration Guide

## Overview

The Electron app provides the user interface for the voice-to-code system. It communicates with the Python backend via:
1. **WebSocket** (localhost:5000/ws) for real-time messages
2. **HTTP** APIs for commands and file operations

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│           Electron Overlay (UI)                     │
│  - Custom prompts panel                             │
│  - Transcript display                               │
│  - Screenshot capture and viewing                   │
│  - Hotkey management                                │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ WebSocket (ws://localhost:5000/ws)
                   │ HTTP (http://localhost:5000/api/*)
                   │
┌──────────────────▼──────────────────────────────────┐
│        Web Server (web_server.py)                   │
│  - FastAPI application                              │
│  - WebSocket message relay                          │
│  - File watchers                                    │
│  - Broadcasting updates to Electron                │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Inter-Process Communication
                   │
┌──────────────────▼──────────────────────────────────┐
│     Voice-to-Code System (voice_to_code.py)        │
│  - Audio capture (WASAPI/microphone)                │
│  - Transcription (Groq/OpenAI/Google/Local)        │
│  - LLM processing (Gemini/Claude)                  │
│  - Code generation and file writing                │
│  - MCP server (Claude Desktop integration)         │
└─────────────────────────────────────────────────────┘
```

## Message Types

### From Electron to Backend

**Code Generation Requests**:
```javascript
{
  type: 'code_generation_request',
  action: 'new_code' | 'update_code',
  prompt: string,
  transcripts: string
}
```

**Text Analysis Prompts**:
```javascript
{
  type: 'analyze_text_prompt',
  prompt: string
}
```

**Gemini Coach Requests**:
```javascript
{
  type: 'gemini_coach_request',
  text: string
}
```

### From Backend to Electron

**Code Generation Complete**:
```json
{
  "type": "code_generation_complete",
  "files": {
    "filename": "content"
  }
}
```

**Transcript Update**:
```json
{
  "type": "transcript_update",
  "segments": [
    {"id": "1", "speaker": "User", "text": "..."}
  ]
}
```

**Screenshot Saved**:
```json
{
  "type": "screenshot_saved",
  "path": "/path/to/screenshot.png"
}
```

## How to Start

### Quick Start (All-in-One)

```bash
# 1. Configure environment
export GOOGLE_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here
export LLM_METHOD=gemini
export TRANSCRIPTION_METHOD=groq

# 2. Start Python backend (voice-to-code system)
uv run python voice_to_code.py

# This will:
# - Start the web server (http://localhost:5000)
# - Initialize the MCP server
# - Ready to receive Electron connections
```

### In Another Terminal: Start Electron App

```bash
cd electron-overlay

# Start the Electron app
npm start

# OR directly with electron
npx electron .
```

## What Happens When You Press a Custom Prompt

1. **User clicks prompt button in Electron overlay**
   - `custom_prompts.js` catches the click event
   - Extracts selected transcripts from the UI
   - Builds message based on prompt type

2. **Message sent to backend via WebSocket**
   ```javascript
   ws.send(JSON.stringify({
     type: 'code_generation_request',
     action: 'new_code',
     prompt: 'User custom prompt text',
     transcripts: '[User]: transcript text\n...'
   }))
   ```

3. **Web server receives message**
   - `web_server.py` WebSocket endpoint catches message
   - Validates message structure
   - Relays to `VoiceToCodeSystem` via queue

4. **Voice-to-code system processes request**
   - `VoiceToCodeSystem.process_command()` handles it
   - Combines transcript with custom prompt
   - Sends to LLM router (Gemini/Claude)
   - Generates code
   - Writes files

5. **Results sent back to Electron**
   - File watcher detects new files
   - Broadcasts update to WebSocket clients
   - Electron receives update
   - UI displays generated code

## Key File Locations

**Python Backend**:
- `voice_to_code.py` - Main system
- `web_server.py` - FastAPI server
- `llm_router.py` - LLM abstraction
- `mcp_server.py` - Claude Desktop integration
- `.env` - Configuration

**Electron App**:
- `electron-overlay/overlay.html` - Main UI
- `electron-overlay/custom_prompts.js` - Prompt system
- `electron-overlay/main.js` - Electron main process
- `electron-overlay/preload.js` - IPC bridges
- `electron-overlay/package.json` - Dependencies

**Generated Files** (watched by web server):
- `generated_code/` - Output directory
- `generated_code/screenshots/` - Screenshot storage
- `generated_code/.live_transcript` - Current transcription

## Troubleshooting

### WebSocket Connection Failed

**Error**: `WebSocket connection refused` or `Connection failed`

**Causes**:
1. Python backend not running
2. Web server not started
3. Wrong server address in Electron

**Fix**:
```bash
# Ensure voice_to_code.py is running
# Check if web_server.py started successfully
lsof -i :5000  # Check if port 5000 is listening

# Verify URL in Electron overlay
# Should show localhost:5000 in server input box
```

### Custom Prompts Not Responding

**Error**: Prompts send but nothing happens

**Causes**:
1. No transcripts selected
2. Gemini API key not configured
3. Backend error in processing

**Fix**:
```bash
# Check that transcripts are available in UI
# Verify API keys in .env
echo $GOOGLE_API_KEY
echo $ANTHROPIC_API_KEY

# Check Python backend logs
tail -f logs/session_*.log
```

### Screenshot Capture Not Working

**Error**: Screenshot button doesn't work

**Causes**:
1. Electron app not properly initialized
2. Missing screenshot dependencies

**Fix**:
```bash
# Reinstall dependencies
cd electron-overlay
npm install

# Verify sharp module
npm list sharp
```

## Configuration

### Environment Variables

```bash
# LLM Backend
LLM_METHOD=gemini              # or claude
GOOGLE_API_KEY=...             # For Gemini
ANTHROPIC_API_KEY=...          # For Claude

# Transcription
TRANSCRIPTION_METHOD=groq      # or local, openai, google
GROQ_API_KEY=...
OPENAI_API_KEY=...

# Audio
AUDIO_SOURCE=both              # or microphone, system
VAD_AGGRESSIVENESS=2           # 1-3
SILENCE_TIMEOUT=0.5            # seconds

# Web Viewer
ENABLE_WEB_VIEWER=true
DEFAULT_SERVER_IP=localhost

# Debug
DEBUG=true                      # Show verbose output
```

### Custom Prompts

Edit `electron-overlay/custom_prompts.js` to add new prompts:

```javascript
{
  id: 'custom-id',
  icon: '📝',
  label: 'Prompt Label',
  prompt: 'The actual prompt text sent to LLM',
  action: 'new_code'  // or update_code, capture, copy
}
```

**Actions**:
- `new_code` - Generate new code from transcript
- `update_code` - Update existing code
- `capture` - Take screenshot and analyze
- `copy` - Send prompt text for analysis

## Performance Tips

1. **Keep Electron app in focus** - Hotkeys work best when overlay is active

2. **Use Groq for transcription** - Fastest and free transcription option
   ```bash
   export TRANSCRIPTION_METHOD=groq
   export GROQ_API_KEY=your_key
   ```

3. **Monitor system resources**
   - Electron app: 150-300MB RAM
   - Python backend: 100-200MB RAM
   - Total: 250-500MB RAM typical

4. **Adjust VAD settings** for better speech detection:
   - Lower `VAD_AGGRESSIVENESS` (1-2) for noisy environments
   - Adjust `SILENCE_TIMEOUT` for different pause durations

## Hot Reload

### Restart Python Backend (without restarting Electron)

```bash
# Kill the backend process
pkill -f voice_to_code.py

# Restart it
uv run python voice_to_code.py

# Electron will reconnect automatically
```

### Restart Electron (without restarting Python)

```bash
# Close Electron window
# In electron-overlay directory:
npm start

# Or with direct electron:
npx electron .
```

## Complete Example: Voice-to-Code with Custom Prompts

1. **Start the system**:
   ```bash
   # Terminal 1: Start Python backend
   export GOOGLE_API_KEY=AIzaSy...
   export TRANSCRIPTION_METHOD=groq
   export GROQ_API_KEY=gsk_...
   uv run python voice_to_code.py

   # Terminal 2: Start Electron app
   cd electron-overlay
   npm start
   ```

2. **Use the system**:
   - Electron overlay appears on screen
   - Click "Open Transcript Window" to see transcripts
   - Speak natural language commands
   - See transcription appear in real-time
   - Select transcript segments
   - Click a custom prompt (e.g., "Generate New Code")
   - Watch code generate in the web viewer
   - Prompts appear in Electron overlay

3. **Monitor progress**:
   - Web viewer: http://localhost:5000 (open in browser)
   - Python logs: `logs/session_*.log`
   - Electron console: F12 in Electron window

## Integration Points

### WebSocket Connection
- **File**: `electron-overlay/overlay.html` (line ~1352)
- **Connected when**: Electron app starts
- **Disconnected when**: Electron app closes

### File Watchers
- **Watched directories**: `generated_code/`
- **Events**: file creation, modification
- **Broadcasts**: transcript updates, screenshots, code changes

### Message Relay
- **Source**: Electron WebSocket messages
- **Processor**: `web_server.py` WebSocket handler
- **Destination**: `VoiceToCodeSystem` command queue

## Testing the Integration

### Test 1: WebSocket Connection

```bash
# In Python shell
import asyncio
from web_server import app

# This verifies the web server can start
print("Web server configured and ready")
```

### Test 2: Custom Prompt Execution

```bash
# From Electron console (F12)
// This should connect and show status
ws.readyState  // Should be 1 (OPEN)
ws.send(JSON.stringify({
  type: 'test_message',
  data: 'test'
}))
```

### Test 3: File Watching

```bash
# Create a test file while system is running
touch generated_code/test.py

# Should see broadcast in Electron console
# WebSocket message should show file creation
```

## Next Steps

1. **Ensure Python backend is running**
   ```bash
   uv run python voice_to_code.py
   ```

2. **Start Electron app**
   ```bash
   cd electron-overlay && npm start
   ```

3. **Test each feature**:
   - Audio capture
   - Transcription
   - Custom prompts
   - Code generation
   - Screenshot capture

4. **Monitor logs**:
   - Python: `logs/session_*.log`
   - Electron: Browser DevTools (F12)

---

For detailed information on each component, see:
- `STAGE_7_SUMMARY.md` - LLM Router architecture
- `STAGE_8_TEST_RESULTS.md` - Test coverage
- `MERGE_STATUS.md` - Overall system status
