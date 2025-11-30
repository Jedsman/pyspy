# Claude Desktop MCP Integration

This integration allows you to use your voice-to-code transcripts and screenshots directly in Claude Desktop **without using the API** and **without any costs**.

## What is MCP?

Model Context Protocol (MCP) is an open protocol that allows Claude Desktop to access external data sources. By running a local MCP server, you can make your interview transcripts and screenshots available to Claude Desktop conversations.

## Features

✅ **No API Costs** - Uses Claude Desktop's existing subscription
✅ **Live Transcript Access** - Claude can read your real-time transcript buffer
✅ **Captured Segments** - Access all manually captured transcript segments
✅ **Screenshot Support** - Share screenshots with Claude for visual context
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

### Example Conversations

**Example 1: Review transcript**
```
You: Can you review my recent interview transcript?

Claude: I'll look at your transcript. [reads transcript://segments]
Based on your conversation, here are some key points...
```

**Example 2: Analyze screenshot**
```
You: I'm stuck on this coding problem, can you help?
[Click capture screenshot button or ask Claude to capture]

Claude: [reads screenshot] I can see the error in your code...
```

**Example 3: Get full context**
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
┌─────────────────────┐
│  Voice-to-Code App  │
│  (voice_to_code.py) │
└──────────┬──────────┘
           │ Writes files
           ▼
┌─────────────────────────────┐
│  generated_code/            │
│  ├── .live_transcript       │ ← Real-time buffer
│  ├── .transcript_history    │ ← Captured segments
│  └── screenshots/           │ ← Screenshots
└──────────┬──────────────────┘
           │ Reads files
           ▼
┌─────────────────────┐
│   MCP Server        │
│  (mcp_server.py)    │
└──────────┬──────────┘
           │ MCP Protocol
           ▼
┌─────────────────────┐
│  Claude Desktop     │
└─────────────────────┘
```

### File-Based Communication

1. **Live Transcript** - Written to `.live_transcript` in real-time as you speak
2. **Captured Segments** - Appended to `.transcript_history` when you click Capture
3. **Screenshots** - Saved to `screenshots/` directory when captured
4. **Commands** - MCP server can trigger captures via `.command` file

### Data Privacy

All data stays on your local machine:
- Transcripts are never sent to external servers (except when you explicitly use them in Claude conversations)
- Screenshots are stored locally
- MCP server runs entirely on your machine
- Only you control what data Claude Desktop can access

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

## Advanced Usage

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

### Clearing History

To start fresh:

```bash
# Delete transcript history
del generated_code\.transcript_history

# Delete all screenshots
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

## Next Steps

1. ✅ Set up the MCP server (see Setup Instructions above)
2. 📝 Start your voice-to-code app in Coach Mode
3. 💬 Have a practice interview
4. 📋 Capture interesting moments
5. 🤖 Ask Claude Desktop to review your performance!

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [MCP Python SDK](https://github.com/anthropics/python-sdk-mcp)

## Feedback

If you encounter issues or have suggestions, please open an issue on the GitHub repository.
