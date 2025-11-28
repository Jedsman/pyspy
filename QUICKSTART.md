# Quick Start Guide

Get up and running with Voice-to-Code in under 5 minutes!

## Prerequisites

- Windows 10/11 (for loopback audio capture)
- Python 3.8 or higher
- Anthropic API key

## Installation (Using uv - FASTEST)

### 1. Install uv
```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install Voice-to-Code with Local Whisper (FREE)
```bash
cd c:\Users\theje\code\py_llm
uv sync --extra local
```

### 3. Create .env file
```bash
# Create .env file with your API key
echo ANTHROPIC_API_KEY=sk-ant-your-key-here > .env
echo TRANSCRIPTION_METHOD=local >> .env
```

### 4. Run it!
```bash
uv run voice_to_code.py
```

## What Happens Next

1. **System starts** - Loads the local Whisper model (~1GB, first run only)
2. **Audio capture begins** - Listens to your system audio
3. **Join a video call** - Start pair programming!
4. **Discuss code** - Talk about features you want to implement
5. **Code appears** - Check the `generated_code/` folder

## Example Conversation

```
You: "Let's create a Python function that validates email addresses"
Partner: "Good idea, use regex and handle common edge cases"

→ System transcribes conversation
→ Claude analyzes and generates code
→ File saved to: generated_code/20250126_143022_email_validator.py
```

## Switching Transcription Methods

Edit `.env` file:

```bash
# FREE - Local Whisper (default)
TRANSCRIPTION_METHOD=local

# Fast - OpenAI API ($0.006/min)
TRANSCRIPTION_METHOD=openai
OPENAI_API_KEY=sk-...

# Google Cloud (60 free min/month)
TRANSCRIPTION_METHOD=google
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

Then reinstall dependencies:
```bash
# For OpenAI
uv sync --extra openai

# For Google Cloud
uv sync --extra google

# For all options
uv sync --extra all
```

## Troubleshooting

### "No loopback device found"
- Make sure you're on Windows 10/11
- Update your audio drivers

### "Failed to load Whisper model"
```bash
# Install ffmpeg (required by Whisper)
# Download from: https://ffmpeg.org/download.html
# Or use: winget install ffmpeg
```

### "ANTHROPIC_API_KEY not found"
- Check your `.env` file exists
- Verify the API key starts with `sk-ant-`
- Get one at: https://console.anthropic.com/

## Cost Breakdown

| Method | 1-hour call | Notes |
|--------|-------------|-------|
| **Local Whisper** | **$0.20** | FREE transcription + Claude |
| OpenAI Whisper | $0.56 | $0.36 transcription + $0.20 Claude |
| Google Cloud | $1.16 | $0.96 transcription + $0.20 Claude |

## Next Steps

- Read [README_VOICE_TO_CODE.md](README_VOICE_TO_CODE.md) for full documentation
- Adjust voice detection sensitivity
- Customize the code generation prompt
- Set up as a background service

## Need Help?

- Check [Troubleshooting](README_VOICE_TO_CODE.md#troubleshooting) section
- Review the code in `voice_to_code.py`
- Ensure your microphone/speakers are working
