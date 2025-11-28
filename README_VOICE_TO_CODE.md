# Voice-to-Code System

Real-time system that listens to your video calls, transcribes conversations, and automatically generates code based on what's discussed.

## Architecture

```
Video Call Audio (Loopback)
    ↓
Audio Capture (PyAudioWPatch - WASAPI)
    ↓
Voice Activity Detection (Energy-based)
    ↓
Speech Transcription (OpenAI Whisper API)
    ↓
LLM Analysis (Claude 3.5 Sonnet)
    ↓
Code Generation & File Output
```

## Features

- **Real-time Audio Capture**: Uses Windows WASAPI loopback to capture system audio
- **Voice Activity Detection**: Only processes segments with actual speech
- **Automatic Transcription**: OpenAI Whisper transcribes speech to text
- **Intelligent Code Generation**: Claude analyzes conversation context and generates code when appropriate
- **Versioned Output**: Generated code files are timestamped and organized

## Requirements

### System Requirements
- **Windows 10/11** (for WASAPI loopback support)
- Python 3.8+
- Microphone/speakers for audio capture

### API Keys
- **Anthropic API key** (REQUIRED - for Claude code generation)
- **Transcription API keys** (depends on your choice):
  - **Local Whisper**: No API key needed (FREE)
  - **OpenAI Whisper**: OpenAI API key (costs $0.006/min)
  - **Google Cloud**: Google Cloud credentials (60 free min/month)

## Installation

### Option 1: Using uv (RECOMMENDED - Fast!)

[uv](https://github.com/astral-sh/uv) is an extremely fast Python package installer and resolver.

**Install uv:**
```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Install the project with your preferred transcription method:**

#### Option A: Local Whisper (RECOMMENDED - FREE)
```bash
uv sync --extra local
```
- No API costs
- Runs on your computer
- Requires ~1GB download for model

#### Option B: OpenAI Whisper API
```bash
uv sync --extra openai
```
- Costs $0.006/min
- Fastest and most accurate
- Requires OpenAI API key

#### Option C: Google Cloud Speech-to-Text
```bash
uv sync --extra google
```
- 60 free minutes/month
- Then $0.016/min
- Requires Google Cloud setup

#### Option D: Install All Methods
```bash
uv sync --extra all
```

### Option 2: Using pip (Traditional)

**Install base dependencies:**
```bash
pip install -r requirements.txt
```

**Choose your transcription method:**

#### Option A: Local Whisper (RECOMMENDED - FREE)
```bash
pip install openai-whisper
```

#### Option B: OpenAI Whisper API
```bash
pip install openai
```

#### Option C: Google Cloud Speech-to-Text
```bash
pip install google-cloud-speech
```

## Configuration

### 1. Configure API Keys and Method

Create a `.env` file in the project root:
```bash
# REQUIRED - for code generation
ANTHROPIC_API_KEY=sk-ant-...

# Choose transcription method: local, openai, or google
TRANSCRIPTION_METHOD=local

# If using OpenAI (TRANSCRIPTION_METHOD=openai)
OPENAI_API_KEY=sk-...

# If using Google Cloud (TRANSCRIPTION_METHOD=google)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-key.json
```

### 2. Test Audio Setup

On Windows, make sure your audio output device supports loopback:
- The system will automatically detect your default speakers
- PyAudioWPatch will capture audio from this device

## Usage

### Start the System

**With uv:**
```bash
uv run voice_to_code.py
# or use the installed script
uv run voice-to-code
```

**With pip/python:**
```bash
python voice_to_code.py
```

You'll see:
```
🚀 VOICE-TO-CODE SYSTEM STARTING
📡 Using audio device: Speakers (Realtek High Definition Audio)
🎙️  Audio capture started

📋 System will:
   1. Capture audio from your system (video calls, etc.)
   2. Detect when people are speaking
   3. Transcribe speech to text
   4. Generate code based on conversation
```

### During a Call

1. **Start a video call** (Zoom, Teams, Google Meet, Discord, etc.)
2. **Discuss code/features** - The system listens in the background
3. **Watch the console** for transcriptions and code generation
4. **Check `generated_code/` folder** for output files

### Example Conversation

```
You: "Let's create a Python function that calculates fibonacci numbers"
Colleague: "Good idea, make it recursive with memoization"

System will:
💬 Transcribe the conversation
🤖 Analyze with Claude
✅ Generate: generated_code/20250126_143022_fibonacci.py
```

## How It Works

### 1. Audio Capture (`AudioCapture` class)
- Uses PyAudioWPatch to access WASAPI loopback
- Captures all system audio in real-time
- Chunks audio into manageable segments

### 2. Voice Activity Detection (`VoiceActivityDetector` class)
- Energy-based detection to identify speech
- Reduces API calls by only processing speech segments
- Waits for ~2 seconds of silence before processing

### 3. Speech Transcription (`SpeechTranscriber` class)
- Supports three transcription methods:
  - **Local Whisper**: FREE, runs on your machine
  - **OpenAI API**: Fast, cloud-based ($0.006/min)
  - **Google Cloud**: 60 free min/month ($0.016/min after)
- Returns text transcription
- Handles temporary WAV file creation

### 4. Code Generation (`CodeGenerator` class)
- Maintains conversation context (last 10 exchanges)
- Uses Claude with specialized system prompt
- Only generates code when conversation is specific enough
- Outputs JSON with files, descriptions, and reasoning

### 5. Main Orchestrator (`VoiceToCodeSystem` class)
- Coordinates all components
- Manages audio buffering
- Handles speech segment processing
- Saves generated code with timestamps

## Configuration

### Switching Transcription Methods

Edit your `.env` file:
```bash
# Use local Whisper (FREE)
TRANSCRIPTION_METHOD=local

# Use OpenAI API ($0.006/min)
TRANSCRIPTION_METHOD=openai

# Use Google Cloud (60 free min/month)
TRANSCRIPTION_METHOD=google
```

### Adjusting Local Whisper Model Size

In `voice_to_code.py:147`, change the model:
```python
self.local_model = whisper.load_model("base")
```

Available models (larger = better quality, slower):
- `tiny` - Fastest, lowest quality (~75MB)
- `base` - Good balance (default, ~150MB)
- `small` - Better quality (~500MB)
- `medium` - High quality (~1.5GB)
- `large` - Best quality (~3GB)

### Adjusting Voice Detection Sensitivity

In `voice_to_code.py`, modify:
```python
self.vad = VoiceActivityDetector(threshold=500)  # Lower = more sensitive
```

### Changing Silence Duration

```python
if self.silence_counter > 40:  # Adjust for longer/shorter pauses
```

### Modifying System Prompt

Edit the `CodeGenerator.system_prompt` to customize when and how code is generated.

## Output

Generated code appears in `generated_code/` with format:
```
generated_code/
├── 20250126_143022_fibonacci.py
├── 20250126_144530_api_handler.py
└── 20250126_145012_database_model.py
```

Each file includes:
- Timestamp for version tracking
- Clean, production-ready code
- Auto-generated based on conversation

## Troubleshooting

### "No loopback device found"
- Make sure you're on Windows 10/11
- Check that your audio drivers support WASAPI
- Try updating audio drivers

### "Transcription error"
**Local Whisper:**
- Run: `pip install openai-whisper`
- Make sure you have enough disk space (~1GB for model)
- Check if ffmpeg is installed (required by Whisper)

**OpenAI API:**
- Verify OPENAI_API_KEY is set correctly
- Check your OpenAI account has credits
- Ensure audio quality is good

**Google Cloud:**
- Verify GOOGLE_APPLICATION_CREDENTIALS points to valid JSON key
- Check you have Speech-to-Text API enabled in GCP console
- Verify you haven't exceeded free tier (60 min/month)

### "LLM processing error"
- Verify ANTHROPIC_API_KEY is set correctly
- Check your Anthropic account status
- Review console for specific error messages

### No code being generated
- System only generates when conversation is specific
- Try being more explicit: "Let's write a function that..."
- Check console for LLM reasoning

### Local Whisper is too slow
- Use a smaller model: `whisper.load_model("tiny")` in voice_to_code.py:147
- Or switch to OpenAI API: `TRANSCRIPTION_METHOD=openai` in .env
- Consider using a GPU if available (CUDA)

## Advanced Usage

### Running as Background Service

For production use, consider:
- Running as Windows service
- Adding logging to file
- Implementing health checks
- Adding web dashboard

### Extending Code Actions

Modify `CodeGenerator.save_generated_code()` to:
- Automatically commit to git
- Run formatters (black, prettier)
- Execute tests
- Deploy to staging

### Multi-Language Support

Change Whisper language parameter:
```python
transcript = self.client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    language="es"  # Spanish, "fr" for French, etc.
)
```

## Privacy & Security

**IMPORTANT**: This system captures ALL system audio including:
- Your voice
- Other participants' voices
- Any other sounds playing

Considerations:
- Inform meeting participants if recording
- Check company policies on call recording
- Consider data retention policies
- Be aware of sensitive information in calls
- API calls send audio to OpenAI and Anthropic

## Cost Estimation

### Transcription Costs (choose one)

| Method | Cost per Hour | Free Tier | Notes |
|--------|---------------|-----------|-------|
| **Local Whisper** | **$0.00** | Unlimited | FREE! Uses your CPU/GPU |
| OpenAI Whisper | $0.36 | None | Fastest, most accurate |
| Google Cloud STT | $0.96 | 60 min/month | Good for light usage |

### Anthropic Claude (Code Generation)
- ~$3 per million input tokens
- ~$15 per million output tokens
- Typical code generation = $0.01-0.05 per request

### Example: 1-hour coding call

**With Local Whisper (RECOMMENDED):**
- Transcription: **$0.00** (FREE)
- Code generation (10 requests): ~$0.20
- **Total: ~$0.20**

**With OpenAI Whisper:**
- Transcription: ~$0.36
- Code generation (10 requests): ~$0.20
- **Total: ~$0.56**

**With Google Cloud:**
- Transcription: ~$0.96 (after free tier)
- Code generation (10 requests): ~$0.20
- **Total: ~$1.16**

## Future Enhancements

- [ ] Support for macOS/Linux using alternative audio capture
- [ ] Real-time streaming transcription (avoid segment delays)
- [ ] Multi-speaker diarization (who said what)
- [ ] Code context awareness (read existing project files)
- [ ] Interactive approval before generating files
- [ ] Integration with IDEs (VS Code extension)
- [ ] WebSocket server for remote monitoring
- [ ] Database for conversation history
- [ ] Code review and testing integration

## References

- [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) - WASAPI loopback support
- [OpenAI Whisper](https://platform.openai.com/docs/guides/speech-to-text) - Speech transcription
- [Anthropic Claude](https://docs.anthropic.com/claude/docs) - Code generation
- [WhisperLive](https://github.com/collabora/WhisperLive) - Real-time transcription reference

## License

MIT

## Disclaimer

This tool is for educational and productivity purposes. Always respect privacy laws and obtain consent before recording conversations.
