# Claude Desktop MCP Integration

This integration allows you to use your voice-to-code transcripts and screenshots directly in Claude Desktop **without using the API** and **without any costs**.

## What is MCP?

Model Context Protocol (MCP) is an open protocol that allows Claude Desktop to access external data sources. By running a local MCP server, you can make your interview transcripts and screenshots available to Claude Desktop conversations.

## Features

✅ **No API Costs** - Uses Claude Desktop's existing subscription
✅ **Live Transcript Access** - Claude can read your real-time transcript buffer
✅ **Captured Segments** - Access all manually captured transcript segments
✅ **Screenshot Analysis** - Send screenshots with prompts to Claude for visual analysis
✅ **Text Prompts** - Send ad-hoc text analysis requests to Claude
✅ **Code Generation Tasks** - Route code generation requests (new_code/update_code) to Claude
✅ **Dual-LLM Support** - Simultaneously use Gemini and Claude for different tasks
✅ **Interview Context** - Get complete interview context in one command
✅ **Local & Private** - All data stays on your machine

## Setup Instructions

### 1. Install MCP Python SDK

```bash
pip install mcp
```

Or if using `uv`:

```bash
uv pip install mcp
```

### 2. Install Screenshot Dependency

```bash
pip install Pillow
```

Or with `uv`:

```bash
uv pip install Pillow
```

### 3. Configure Claude Desktop

You need to add the MCP server configuration to Claude Desktop's config file.

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

Copy the contents from [claude_desktop_config.json](./claude_desktop_config.json) to your Claude Desktop config file.

**Important:** Update the path in the config to match your actual project location:

```json
{
  "mcpServers": {
    "voice-to-code": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\theje\\code\\py_llm",
        "run",
        "mcp_server.py"
      ]
    }
  }
}
```

If you're not using `uv`, you can use Python directly:

```json
{
  "mcpServers": {
    "voice-to-code": {
      "command": "python",
      "args": [
        "C:\\Users\\theje\\code\\py_llm\\mcp_server.py"
      ]
    }
  }
}
```

### 4. Restart Claude Desktop

After updating the config, completely quit and restart Claude Desktop for the changes to take effect.

### 5. Verify Connection

In Claude Desktop, you should see a small 🔌 icon or "Connected servers" indicator showing that the voice-to-code server is connected.

## Usage

### Available Resources

Once connected, Claude Desktop has access to these resources:

1. **Live Transcript Buffer** (`transcript://live`)
   - Real-time view of ongoing conversation
   - Updates as you speak during interviews

2. **Captured Transcript Segments** (`transcript://segments`)
   - All manually captured transcript segments
   - Preserved history of important moments

3. **Screenshots** (`screenshot:///screenshot_YYYYMMDD_HHMMSS.png`)
   - All captured screenshots
   - Useful for sharing visual context

### Available Tools

Claude Desktop can use these tools:

1. **capture_transcript**
   - Captures the current live buffer as a permanent segment
   - Same as pressing the Capture button

2. **capture_screenshot**
   - Takes a screenshot of your current screen
   - Saves to `generated_code/screenshots/`

3. **get_interview_context**
   - Gets complete interview context including all transcripts and screenshots
   - Useful for getting caught up on the conversation

4. **check_prompt_queue**
   - Checks for pending analysis requests (screenshots + prompts, text prompts)
   - Returns next queued item with screenshot/text and analysis prompt
   - Automatically removes processed items from queue
   - Perfect for reviewing what the Electron app wants Claude to analyze

5. **check_code_generation_queue**
   - Checks for pending code generation requests from the Electron app
   - Returns action (new_code or update_code), prompt, and relevant transcripts
   - Allows Claude to review and provide feedback on generated code
   - Complements the Gemini-powered code generation pipeline

### Example Conversations

**Example 1: Review transcript**
```
You: Can you review my recent interview transcript?

Claude: I'll look at your transcript. [reads transcript://segments]
Based on your conversation, here are some key points...
```

**Example 2: Check for pending analysis requests**
```
You: What does the Electron app want me to analyze?

Claude: I'll check the prompt queue. [uses check_prompt_queue tool]
I found a screenshot analysis request: "Explain This Code"
Here's the screenshot: [displays image]
Here's what you asked me to analyze: "Explain what this function does and identify any potential bugs"
Let me analyze this for you...
```

**Example 3: Review code generation suggestions**
```
You: What code generation requests are pending?

Claude: I'll check for any pending code generation requests. [uses check_code_generation_queue tool]
I found a code generation request: "Generate new code for user authentication"
Relevant interview context: [shows selected transcripts]
Here's my feedback on the approach and some suggestions...
```

**Example 4: Get full context**
```
You: What have we discussed so far in this interview?

Claude: [uses get_interview_context tool]
Here's a summary of your interview so far:
- You discussed your experience with...
- The interviewer asked about...
```

## How It Works

### Architecture

```
┌──────────────────────────────┐
│   Electron Overlay App       │
│   (Custom Prompts UI)        │
└──────────┬───────────────────┘
           │ IPC (Inter-Process Communication)
           ▼
┌──────────────────────────────┐
│   Electron Main Process      │
│   (main.js)                  │
└──────────┬───────────────────┘
           │ Writes files to shared drive
           ▼
┌──────────────────────────────────────┐
│   shared_drive/generated_code/       │
│   ├── .live_transcript               │ ← Real-time transcript buffer
│   ├── .transcript_history            │ ← Captured segments
│   ├── .command                       │ ← Gemini requests
│   ├── .prompt_queue.json             │ ← Claude analysis requests
│   ├── .code_generation_queue.json    │ ← Claude code generation requests
│   ├── screenshots/                   │
│   │   ├── capture-XXX.png           │ ← Screenshot images
│   │   └── capture-XXX.txt           │ ← Analysis prompts
│   └── ...                            │
└──────────┬──────────────────────────┘
           │ File watching
           ▼
┌──────────────────────────────┐    ┌──────────────────────────┐
│   voice_to_code.py           │    │   mcp_server.py          │
│   (Gemini LLM Router)        │    │   (Claude Desktop Bridge) │
└──────────┬───────────────────┘    └──────────┬───────────────┘
           │ Gemini API calls              │ MCP Protocol
           ▼                                ▼
┌──────────────────────────────┐    ┌──────────────────────────┐
│   Gemini API                 │    │   Claude Desktop         │
│   (Fast code generation)     │    │   (Analysis & Review)    │
└──────────────────────────────┘    └──────────────────────────┘
```

### File-Based Communication

1. **Live Transcript** - Written to `.live_transcript` in real-time as you speak
2. **Captured Segments** - Appended to `.transcript_history` when you click Capture
3. **Screenshots** - Saved to `screenshots/` directory when captured
   - `capture-YYYYMMDD_HHMMSS.png` - The screenshot image
   - `capture-YYYYMMDD_HHMMSS.txt` - The analysis prompt (new)
4. **Gemini Queue** - Requests written to `.command` file for Gemini processing
5. **Claude Analysis Queue** - Text/screenshot analysis requests written to `.prompt_queue.json`
6. **Claude Code Generation Queue** - Code generation requests written to `.code_generation_queue.json`

### Data Privacy

All data stays on your local machine:
- Transcripts are never sent to external servers (except when you explicitly use them in Claude conversations)
- Screenshots are stored locally
- MCP server runs entirely on your machine
- Only you control what data Claude Desktop can access

## Dual-LLM Workflow Guide

This system is designed to leverage both Gemini and Claude for different strengths:

### When to Use Gemini (via the Electron app)
- **Fast code generation** - Gemini specializes in rapid code synthesis
- **Real-time feedback** - Results appear immediately in the overlay
- **Iterative coding** - Update code on the fly during interviews
- **Default for code** - Code generation (new_code/update_code) always goes to Gemini

### When to Use Claude (via Claude Desktop)
- **Detailed analysis** - Claude excels at thoughtful code review
- **Interview feedback** - Get coaching on your responses
- **Architectural decisions** - Claude provides deeper reasoning on design choices
- **Post-session review** - Claude can review entire interview context
- **Screenshot explanation** - Claude can explain complex code visuals in detail

### Typical Interview Workflow with Dual-LLM

1. **During the interview:**
   - Use Gemini for fast code generation
   - Click prompts like "Explain This Code" or "Find Bugs" to get immediate Gemini analysis
   - Both Gemini AND Claude receive these requests simultaneously
   - Gemini results appear immediately in the overlay

2. **During the interview (Claude review):**
   - Open Claude Desktop in a secondary window (or after interview)
   - Say: "What analysis requests are pending?" → Claude uses `check_prompt_queue` tool
   - Claude shows you the screenshot and analysis prompt
   - Claude provides alternative perspectives or deeper insights

3. **After Gemini generates code:**
   - In Claude Desktop: "What code generation requests are pending?"
   - Claude uses `check_code_generation_queue` tool
   - Claude reviews the generated code and provides feedback
   - Claude might suggest improvements or optimizations

4. **End of interview:**
   - Say: "Summarize my interview performance"
   - Claude uses `get_interview_context` tool to review all transcripts
   - Claude provides comprehensive coaching feedback

### Queue Files Structure

#### .prompt_queue.json (Claude Analysis Queue)
```json
[
  {
    "type": "screenshot",
    "filename": "capture-20251203_223145.png",
    "prompt": "Explain what this code does and identify any potential bugs",
    "timestamp": "2025-12-03T22:31:45Z"
  },
  {
    "type": "text",
    "prompt": "What are good approaches for handling user input validation in a React component?",
    "timestamp": "2025-12-03T22:35:12Z"
  }
]
```

#### .code_generation_queue.json (Claude Code Gen Queue)
```json
[
  {
    "type": "code_generation",
    "action": "new_code",
    "prompt": "Create a React component that manages user authentication",
    "transcripts": "User: How would you build the auth flow? ...\nInterviewer: What about token storage?",
    "timestamp": "2025-12-03T22:40:00Z"
  }
]
```

## Capturing Data

### Manual Capture (Recommended)

**Capture Transcript:**
- Press the **📋 Capture** button in the overlay
- Or use the hotkey: `Ctrl+Shift+C`
- Or ask Claude to use the `capture_transcript` tool

**Capture Screenshot:**
- Ask Claude: "Can you capture a screenshot?"
- Claude will use the `capture_screenshot` tool
- Screenshot is saved and immediately available

### Automatic Capture

The live transcript buffer is automatically updated as you speak, so Claude always has access to the most recent conversation.

## Troubleshooting

### "MCP server not connected"

1. Check that `mcp_server.py` exists in your project directory
2. Verify the path in `claude_desktop_config.json` is correct
3. Make sure `mcp` package is installed: `pip install mcp`
4. Restart Claude Desktop completely (quit and reopen)
5. Check `mcp_server.log` for detailed error messages

### "No transcripts available"

1. Make sure the voice-to-code app is running
2. Speak something to generate a transcript
3. Click the Capture button to save a segment
4. Check that `generated_code/.transcript_history` exists

### "Screenshot capture failed"

1. Install Pillow: `pip install Pillow`
2. Make sure you have permission to capture screenshots
3. On some systems, you may need to grant screenshot permissions

### "Permission denied" errors

- Make sure the `generated_code/` directory exists and is writable
- On Windows, ensure your antivirus isn't blocking file access
- Check that the MCP server has permission to read the directory
- Verify `SHARED_DRIVE_PATH` environment variable points to accessible directory

### "check_prompt_queue returns 'No pending analysis requests'"

1. Verify you clicked a prompt that triggers screenshot/text analysis
   - Screenshots: "Explain This Code", "Find Bugs", "Optimize This", etc.
   - Text: "Prep for Behavioral Question", "Clarify Your Approach", etc.
2. Check that `.prompt_queue.json` exists in your shared drive's `generated_code/` directory
3. Look at `mcp_server.log` to see if queue file is being read
4. Verify Electron console shows `[SCREENSHOT]` or `[TEXT]` log messages when you click prompts
5. Make sure the Electron app is running on the machine with shared drive write access

### "check_code_generation_queue returns 'No pending code generation requests'"

1. Click "Generate New Code" or "Update Code" button in the Electron overlay
2. Verify transcripts are selected (checkboxes checked)
3. Check that `.code_generation_queue.json` exists in shared drive's `generated_code/` directory
4. Look at `mcp_server.log` to see queue file access attempts
5. Verify Electron console shows `[CODE-GEN]` log messages
6. Ensure destination selector includes "Send to Claude Desktop" option

### "Queue files are on local PC, not shared drive"

1. Check that `SHARED_DRIVE_PATH` environment variable is set correctly
   - Windows: `set SHARED_DRIVE_PATH=\\server\share\path`
   - Linux/Mac: `export SHARED_DRIVE_PATH=/mnt/shared/path`
2. Verify the path is accessible from both PC running Electron and PC running MCP server
3. Test file write permission: Create a test file manually in the directory
4. Restart Electron app after changing environment variables

### "mcp_server.log is not being created"

1. Verify mcp_server.py has been updated with logging configuration (see mcp_server.py lines 27-35)
2. Check that log directory exists and is writable
3. Run mcp_server.py directly (not via Claude Desktop) to see console output:
   ```bash
   python mcp_server.py
   ```
4. Check for Python errors in the output

## Advanced Usage

### Configuring Queue Paths

By default, queue files are stored in the `generated_code/` directory. To use a custom shared drive path, set the environment variable:

**Windows (Command Prompt):**
```bash
set SHARED_DRIVE_PATH=\\server\share\interview-data
```

**Windows (PowerShell):**
```powershell
$env:SHARED_DRIVE_PATH="\\server\share\interview-data"
```

**Linux/macOS:**
```bash
export SHARED_DRIVE_PATH=/mnt/shared/interview-data
```

The queue files will then be created at:
- `$SHARED_DRIVE_PATH/.prompt_queue.json`
- `$SHARED_DRIVE_PATH/.code_generation_queue.json`

### Monitoring Queue Files

To debug queue issues, periodically check the queue files while running:

**Prompt Queue:**
```bash
cat generated_code/.prompt_queue.json | python -m json.tool
```

**Code Generation Queue:**
```bash
cat generated_code/.code_generation_queue.json | python -m json.tool
```

**MCP Server Log:**
```bash
tail -f generated_code/mcp_server.log
```

### Custom Screenshot Hotkey

You can add a hotkey for screenshots by modifying the voice-to-code app. Edit `.env`:

```env
SCREENSHOT_HOTKEY=ctrl+shift+s
```

Then register it in `voice_to_code.py` (similar to the capture hotkey).

### Filtering Transcripts

The MCP server returns the last 10 captured segments by default. To change this, edit `mcp_server.py`:

```python
# In get_interview_context tool
for i, segment in enumerate(segments[-10:], 1):  # Change -10 to desired number
```

### Customizing Queue Processing

If you want the MCP server to keep processed items instead of deleting them, edit `mcp_server.py`:

```python
# In check_prompt_queue or check_code_generation_queue handler
# Comment out or modify the write-back that deletes items:
# queue.pop(0)  # Remove this line to keep items
```

### Clearing History

To start fresh:

**Remove queue files:**
```bash
# Clear prompt queue
rm generated_code/.prompt_queue.json

# Clear code generation queue
rm generated_code/.code_generation_queue.json
```

**Remove transcript history:**
```bash
rm generated_code/.transcript_history
```

**Remove all screenshots:**
```bash
rm -r generated_code/screenshots/*
```

**Windows equivalent:**
```bash
del generated_code\.prompt_queue.json
del generated_code\.code_generation_queue.json
del generated_code\.transcript_history
del generated_code\screenshots\*.png
```

## Cost Comparison

| Method | Cost | Limits |
|--------|------|--------|
| **MCP Integration** | $0 (uses Claude Desktop subscription) | No extra cost |
| **Direct API** | ~$0.003 per 1K tokens | Pay per use |
| **Gemini API** | Free tier available | Rate limits |

With MCP, you get unlimited Claude conversations about your transcripts and screenshots using your existing Claude Desktop subscription!

## Security Considerations

- MCP server only exposes data you explicitly capture
- All communication is local (localhost only)
- No data is sent to external servers unless you use it in Claude conversations
- Claude Desktop respects your privacy settings

## Getting Started with Dual-LLM

### Initial Setup

1. ✅ Set up the MCP server (see Setup Instructions above)
2. 🔧 Configure `SHARED_DRIVE_PATH` if using a network drive
3. 📝 Start your voice-to-code app in Coach Mode
4. 💬 Have a practice interview

### First Test: Screenshot Analysis

1. Click "Explain This Code" or another screenshot prompt
2. Take a screenshot of your code
3. **In Electron Console (DevTools):** Look for `[SCREENSHOT] ...` log messages
4. **In Claude Desktop:** Say "What does the Electron app want me to analyze?"
5. Claude will use `check_prompt_queue` tool and show you the screenshot + prompt
6. Gemini also processes simultaneously—check the overlay for analysis

### Second Test: Text Prompt Analysis

1. Click "Prep for Behavioral Question" or another text prompt
2. **In Electron Console:** Look for `[TEXT] Calling sendAdhocPrompt IPC handler...`
3. **In Claude Desktop:** Ask "What analysis requests are pending?"
4. Claude retrieves and shows the text prompt
5. Gemini also displays results in the overlay

### Third Test: Code Generation with Claude Review

1. Select transcript segments
2. Click "Generate New Code" and provide a prompt
3. **In Gemini:** Code appears immediately in the overlay
4. **In Claude Desktop:** Ask "What code generation requests are pending?"
5. Claude reviews the generated code and provides feedback

### Best Practices

- **Monitor mcp_server.log** during testing to see queue file access
- **Use secondary window** to keep Claude Desktop visible while running interviews
- **Check logs regularly** if queue files aren't appearing
- **Verify SHARED_DRIVE_PATH** is accessible from both machines before starting

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [MCP Python SDK](https://github.com/anthropics/python-sdk-mcp)

## Feedback

If you encounter issues or have suggestions, please open an issue on the GitHub repository.
