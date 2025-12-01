"""
Real-Time Voice-to-Code System
Captures audio from video calls, transcribes speech, and generates code using LLM

Architecture:
1. Audio Capture (PyAudioWPatch) -> Loopback audio from system + microphone
2. VAD (WebRTC Voice Activity Detection) -> ML-based speech detection
3. Transcription (Groq/Local Whisper) -> Speech to text
4. LLM Processing (Gemini/Claude) -> Generate code from conversation
5. Code Output -> Write to files
6. Web Viewer (FastAPI + WebSocket) -> Real-time code display

Usage:
    python voice_to_code.py

    Web viewer will be available at http://localhost:5000
"""

import pyaudiowpatch as pyaudio
import wave
import numpy as np
from collections import deque
import threading
import warnings

# Suppress Whisper FP16 warning (FP32 is expected and correct on CPU)
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
import time
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
from datetime import datetime
from pathlib import Path
from enum import Enum
import webrtcvad
import sys
import subprocess
import socket
import urllib.request

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("⚠️  'keyboard' library not installed. Hotkey triggers will be disabled.")
    print("   Install with: uv pip install keyboard")

load_dotenv()


class Logger:
    """Logs output to both console and file"""
    def __init__(self, log_file="session.log"):
        self.log_file = Path(log_file)
        self.terminal = sys.stdout
        self.last_was_spinner = False

    def write(self, message):
        self.terminal.write(message)

        # Don't log spinner updates (messages starting with \r that contain "Listening")
        if message.startswith('\r') and 'Listening' in message:
            self.last_was_spinner = True
            return

        # If previous was spinner and this is a newline, write the spinner state once
        if self.last_was_spinner and message == '\n':
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write('[Listening...]\n')
            self.last_was_spinner = False
            return

        # Normal logging
        self.last_was_spinner = False
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(message)

    def flush(self):
        self.terminal.flush()


class TranscriptionMethod(Enum):
    """Available transcription methods"""
    LOCAL_WHISPER = "local"
    OPENAI_WHISPER = "openai"
    GOOGLE_CLOUD = "google"
    GROQ = "groq"  # Ultra-fast Whisper API (FREE)


class LLMMethod(Enum):
    """Available LLM methods for code generation"""
    CLAUDE = "claude"
    GEMINI = "gemini"


class VoiceActivityDetector:
    """WebRTC-based voice activity detection"""

    def __init__(self, threshold=None, frame_length=0.5, aggressiveness=2, sample_rate=16000):
        """
        Initialize WebRTC VAD

        Args:
            threshold: Ignored (kept for backward compatibility)
            frame_length: Ignored (kept for backward compatibility)
            aggressiveness: VAD aggressiveness (1-3, where 3 is most aggressive)
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000 Hz)
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate

        # WebRTC VAD requires specific frame durations (10, 20, or 30 ms)
        # Calculate the number of bytes needed for 30ms frames
        self.frame_duration_ms = 30
        self.bytes_per_frame = int(sample_rate * self.frame_duration_ms / 1000) * 2  # *2 for 16-bit audio

    def is_speech(self, audio_chunk):
        """Check if audio chunk contains speech using WebRTC VAD"""
        if not audio_chunk or len(audio_chunk) < self.bytes_per_frame:
            return False

        # WebRTC VAD requires exact frame sizes (10, 20, or 30ms).
        # We iterate through the chunk and check each valid frame.
        for i in range(0, len(audio_chunk) - self.bytes_per_frame + 1, self.bytes_per_frame):
            frame = audio_chunk[i:i + self.bytes_per_frame]
            try:
                if self.vad.is_speech(frame, self.sample_rate):
                    return True  # Return True on the first detected speech frame
            except Exception:
                # Ignore errors on a single frame, continue checking
                pass
        
        return False


class AudioSource(Enum):
    """Audio source types"""
    MICROPHONE = "microphone"
    SYSTEM = "system"
    BOTH = "both"


class AudioCapture:
    """Captures audio from microphone and/or system (loopback)"""

    def __init__(self, chunk_size=8192, sample_rate=16000, source=AudioSource.BOTH):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.source = source
        self.audio = pyaudio.PyAudio()
        self.mic_stream = None
        self.system_stream = None
        self.is_recording = False

    def get_default_microphone(self):
        """Find the default microphone device"""
        try:
            default_mic = self.audio.get_default_input_device_info()
            print(f"🎤 Microphone: {default_mic['name']}")
            return default_mic
        except Exception as e:
            print(f"❌ Error finding microphone: {e}")
            return None

    def get_loopback_device(self):
        """Find the default loopback device (WASAPI)"""
        try:
            # Get default WASAPI info
            wasapi_info = self.audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self.audio.get_device_info_by_index(
                wasapi_info["defaultOutputDevice"]
            )

            # Check if loopback is supported
            if not default_speakers["isLoopbackDevice"]:
                for loopback in self.audio.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break

            print(f"🔊 System Audio: {default_speakers['name']}")
            return default_speakers

        except Exception as e:
            print(f"❌ Error finding loopback device: {e}")
            print("💡 Make sure you're on Windows with WASAPI support")
            return None

    def start_capture(self, mic_callback=None, system_callback=None):
        """Start capturing audio from selected sources"""

        if self.source in [AudioSource.MICROPHONE, AudioSource.BOTH]:
            mic_device = self.get_default_microphone()
            if mic_device and mic_callback:
                self.mic_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,  # Mono for microphone
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    input_device_index=mic_device["index"],
                    stream_callback=lambda in_data, fc, ti, status:
                        (in_data, pyaudio.paContinue) if mic_callback(in_data) else (in_data, pyaudio.paComplete)
                )
                self.mic_stream.start_stream()

        if self.source in [AudioSource.SYSTEM, AudioSource.BOTH]:
            system_device = self.get_loopback_device()
            if system_device and system_callback:
                self.system_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=system_device["maxInputChannels"],
                    rate=int(system_device["defaultSampleRate"]),
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    input_device_index=system_device["index"],
                    stream_callback=lambda in_data, fc, ti, status:
                        (in_data, pyaudio.paContinue) if system_callback(in_data) else (in_data, pyaudio.paComplete)
                )
                self.system_stream.start_stream()

        self.is_recording = True
        print("🎙️  Audio capture started")

    def stop_capture(self):
        """Stop audio capture"""
        self.is_recording = False
        if self.mic_stream:
            if self.mic_stream.is_active():
                self.mic_stream.stop_stream()
            self.mic_stream.close()
            self.mic_stream = None
        if self.system_stream:
            if self.system_stream.is_active():
                self.system_stream.stop_stream()
            self.system_stream.close()
            self.system_stream = None
        print("⏹️  Audio capture stopped")

    def cleanup(self):
        """Clean up resources"""
        self.stop_capture()
        self.audio.terminate()


class SpeechTranscriber:
    """Transcribes audio using various methods: Local Whisper, OpenAI API, or Google Cloud"""

    def __init__(self, method=TranscriptionMethod.LOCAL_WHISPER):
        self.method = method
        self.client = None
        self.local_model = None
        self.google_client = None

        # Initialize based on method
        if method == TranscriptionMethod.OPENAI_WHISPER:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI not installed. Run: uv sync --extra openai"
                )
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in .env")
            self.client = OpenAI(api_key=api_key)
            print("🔧 Using OpenAI Whisper API")

        elif method == TranscriptionMethod.LOCAL_WHISPER:
            try:
                import whisper
                print("🔧 Loading local Whisper model (this may take a moment)...")
                # Get model size from environment, default to 'tiny' for speed
                # Options: tiny (fastest), base, small, medium, large (slowest)
                model_size = os.getenv("WHISPER_MODEL", "tiny")
                self.local_model = whisper.load_model(model_size)
                print(f"✅ Local Whisper '{model_size}' model loaded (FREE transcription)")
            except ImportError:
                raise ImportError(
                    "Local Whisper not installed. Run: uv sync --extra local"
                )

        elif method == TranscriptionMethod.GROQ:
            try:
                from groq import Groq
            except ImportError:
                raise ImportError(
                    "Groq not installed. Run: uv sync --extra groq"
                )
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not found in .env")
            self.groq_client = Groq(api_key=api_key)
            print("🔧 Using Groq Whisper API (ULTRA-FAST, FREE)")

        elif method == TranscriptionMethod.GOOGLE_CLOUD:
            try:
                from google.cloud import speech
                self.google_client = speech.SpeechClient()
                print("🔧 Using Google Cloud Speech-to-Text (60 free min/month)")
            except ImportError:
                raise ImportError(
                    "Google Cloud Speech not installed. Run: pip install google-cloud-speech"
                )
            except Exception as e:
                raise Exception(
                    f"Google Cloud credentials error: {e}\n"
                    "Set GOOGLE_APPLICATION_CREDENTIALS env var to your JSON key file"
                )

    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file to text using selected method"""
        try:
            if self.method == TranscriptionMethod.LOCAL_WHISPER:
                return self._transcribe_local(audio_file_path)
            elif self.method == TranscriptionMethod.OPENAI_WHISPER:
                return self._transcribe_openai(audio_file_path)
            elif self.method == TranscriptionMethod.GROQ:
                return self._transcribe_groq(audio_file_path)
            elif self.method == TranscriptionMethod.GOOGLE_CLOUD:
                return self._transcribe_google(audio_file_path)
        except Exception as e:
            print(f"❌ Transcription error ({self.method.value}): {e}")
            return None

    def _transcribe_local(self, audio_file_path):
        """Transcribe using local Whisper model (FREE)"""
        result = self.local_model.transcribe(audio_file_path, language="en")
        return result["text"]

    def _transcribe_openai(self, audio_file_path):
        """Transcribe using OpenAI Whisper API"""
        with open(audio_file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        return transcript.text

    def _transcribe_groq(self, audio_file_path):
        """Transcribe using Groq's ultra-fast Whisper API (FREE)"""
        with open(audio_file_path, "rb") as audio_file:
            transcript = self.groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="en",
                response_format="text"
            )
        return transcript

    def _transcribe_google(self, audio_file_path):
        """Transcribe using Google Cloud Speech-to-Text"""
        from google.cloud import speech

        with open(audio_file_path, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            audio_channel_count=1,
        )

        response = self.google_client.recognize(config=config, audio=audio)

        # Combine all transcripts
        transcript = " ".join([result.alternatives[0].transcript for result in response.results])
        return transcript if transcript else None


from typing import List
from pydantic import BaseModel, Field
from config import GENERATED_CODE_DIR

class CodeGenerator:
    """Generates code using LLM based on a running conversation context."""

    def __init__(self, output_dir=GENERATED_CODE_DIR, llm_method=LLMMethod.GEMINI):
        self.llm_method = llm_method
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.conversation_history = []
        self.active_file_path = None

        # Define Pydantic models for Gemini Function Calling
        class FileInfo(BaseModel):
            """Represents a single file to be generated or updated."""
            filename: str = Field(..., description="The name of the file to be created, or the name of the file being updated.")
            content: str = Field(..., description="The complete source code or content of the file.")
            description: str = Field(..., description="A brief description of what this file does.")

        class GenerateFiles(BaseModel):
            """A tool to generate one or more files, or to update an existing file."""
            files: List[FileInfo] = Field(..., description="A list of files to be generated or updated.")

        # Load system prompt from file
        self.system_prompt = self.load_system_prompt()

        # Initialize LLM client based on method
        if llm_method == LLMMethod.CLAUDE:
            # Claude implementation would need similar architectural changes
            raise NotImplementedError("Context-aware architecture not implemented for Claude yet.")

        elif llm_method == LLMMethod.GEMINI:
            if not self.system_prompt:
                raise ValueError(
                    "Gemini system prompt could not be loaded. "
                    "Please ensure 'prompts/gemini_code_gen.md' exists."
                )
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in .env")
            genai.configure(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

            self.gemini_model = genai.GenerativeModel(
                model_name=model_name,
                tool_config={'function_calling_config': 'ANY'},
                tools=[GenerateFiles]
            )
            print(f"🔧 Using {model_name} with Function Calling for code generation (FREE)")

    def load_system_prompt(self, prompt_filename="prompts/gemini_code_gen.md"):
        """Loads the system prompt from a file."""
        try:
            prompt_path = Path(__file__).parent / prompt_filename
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ System prompt file not found at: {prompt_path}")
            return None


    def set_active_file(self, filename: str):
        """Sets a file as the active target for edits."""
        # Look for the file in the output directory
        target_file = self.output_dir / filename
        if target_file.exists() and target_file.is_file():
            self.active_file_path = target_file
            print(f"✅ File '{filename}' is now active for editing.")
            # Clear history to start fresh with the new context
            self.conversation_history.clear()
            return True
        else:
            print(f"⚠️  File '{filename}' not found in '{self.output_dir}'. Cannot set as active.")
            self.active_file_path = None
            return False

    def close_active_file(self):
        """Closes the currently active file and clears conversation history."""
        if self.active_file_path:
            print(f"✅ Closed file '{self.active_file_path.name}'.")
            self.active_file_path = None
        else:
            print("🤷 No active file to close.")

        if self.conversation_history:
            self.conversation_history.clear()
            print("ⓘ Conversation history cleared.")


    def update_context(self, transcript_text: str):
        """Adds a new transcript to the conversation history."""
        print(f"\n📝 {transcript_text}")
        self.conversation_history.append(transcript_text)

    def generate_code_from_context(self):
        """Processes the conversation history and active file to generate/update code."""
        if not self.conversation_history:
            print("🤖 LLM: No conversation history to process.")
            return

        print("\n🤖 Processing context to generate/update code...")
        
        active_file_content = None
        if self.active_file_path and self.active_file_path.exists():
            print(f"📝 Reading active file: {self.active_file_path.name}")
            with open(self.active_file_path, 'r', encoding='utf-8') as f:
                active_file_content = f.read()

        conversation = "\n".join(self.conversation_history)

        try:
            if self.llm_method == LLMMethod.GEMINI:
                response = self._process_with_gemini(
                    conversation=conversation, 
                    active_file_content=active_file_content
                )

                # Check if the model decided to call the function
                if response.candidates and response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]
                    if hasattr(part, 'function_call'):
                        function_call = part.function_call
                        if function_call.name == 'GenerateFiles' or function_call.name == 'generate_files':
                            print("✅ LLM decided to generate/update code.")
                            args = {key: val for key, val in function_call.args.items()}
                            self.save_generated_code(args['files'])

                        return

                # If no function call was made, log it as an error.
                # This should not happen with the new prompt.
                print("❌ LLM did not call the `GenerateFiles` tool as instructed.")
                if response.text:
                    print(f"🤖 LLM Text Response: {response.text}")
                else:
                    # Log the full response if debug is on for deeper analysis
                    if os.getenv("DEBUG", "false").lower() == "true":
                        print(f"🔍 Debug: Full response object: {response}")

        except Exception as e:
            print(f"❌ LLM processing error: {e}")

    def _process_with_gemini(self, conversation: str, active_file_content: str | None = None):
        """Process with Gemini API using Function Calling."""
        print("📡 Building prompt and sending request to Gemini API...")

        prompt_parts = [self.system_prompt]

        if active_file_content:
            prompt_parts.append(f"ACTIVE FILE: `{self.active_file_path.name}`\n---\n```\n{active_file_content}\n```\n---")

        prompt_parts.append(f"CONVERSATION HISTORY:\n---\n{conversation}\n---")
        
        prompt_parts.append("Based on the conversation, you must now call the `GenerateFiles` tool to produce the required code file(s).")

        prompt = "\n".join(prompt_parts)
        
        if os.getenv("DEBUG", "false").lower() == "true":
            print(f"🔍 --- PROMPT START ---\n{prompt}\n🔍 --- PROMPT END ---")

        try:
            response = self.gemini_model.generate_content(prompt)
            print("✅ Received response from Gemini API")
            return response
        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def save_generated_code(self, files: List[dict]):
        """Saves generated code, overwriting the active file or creating new ones."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for file_info in files:
            filename = file_info["filename"]
            content = file_info["content"]
            description = file_info.get("description", "")
            
            # Check if this file is the active file
            is_active_file = self.active_file_path and self.active_file_path.name == filename
            
            if is_active_file:
                # Overwrite the active file
                filepath = self.active_file_path
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"\n✅ Updated: {filepath}")
                print(f"📝 Description: {description}")
            else:
                # Create a new versioned filename
                filepath = self.output_dir / f"{timestamp}_{filename}"
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"\n✅ Generated: {filepath}")
                print(f"📝 Description: {description}")
                
                # If no file was active, make this new one active
                if not self.active_file_path:
                    print(f"📌 '{filepath.name}' is now the active file.")
                    self.active_file_path = filepath


class InterviewCoach:
    """Provides real-time interview coaching suggestions using Gemini"""

    def __init__(self):
        self.conversation_history = []
        self.system_prompt = self.load_system_prompt()

        # Initialize Gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env")
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.gemini_model = genai.GenerativeModel(model_name=model_name)
        print(f"🎯 Interview Coach initialized with {model_name}")

    def load_system_prompt(self, prompt_filename="prompts/interview_coach.md"):
        """Load the interview coach system prompt"""
        try:
            prompt_path = Path(__file__).parent / prompt_filename
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ Interview coach prompt not found at: {prompt_path}")
            return None

    def add_to_conversation(self, speaker: str, text: str):
        """Add a statement to the conversation history"""
        self.conversation_history.append(f"[{speaker}]: {text}")

    def generate_suggestions(self, question_text: str) -> list:
        """Generate coaching suggestions for an interviewer's question"""
        if not self.system_prompt:
            return ["Error: System prompt not loaded"]

        prompt = f"""{self.system_prompt}

## Interview Question

{question_text}

## Your Task

Generate 3-5 concise, tactical talking points to help the candidate answer this question effectively. Format as bullet points starting with action verbs."""

        try:
            print("📡 Generating interview coaching suggestions...")
            response = self.gemini_model.generate_content(prompt)

            if response.text:
                # Parse the response into bullet points
                suggestions = []
                for line in response.text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                        # Remove bullet point marker
                        suggestion = line.lstrip('-•* ').strip()
                        if suggestion:
                            suggestions.append(suggestion)

                return suggestions if suggestions else [response.text]
            else:
                return ["No suggestions generated"]

        except Exception as e:
            print(f"❌ Error generating suggestions: {e}")
            return [f"Error: {str(e)}"]


class TriggerMode(Enum):
    """Code generation trigger modes"""
    KEYWORD = "keyword"  # Triggered by spoken keyword
    HOTKEY = "hotkey"  # Triggered by keyboard hotkey
    BOTH = "both"  # Either keyword or hotkey


from config import COMMAND_FILE, GENERATED_CODE_DIR, SCREENSHOTS_DIR


class VoiceToCodeSystem:
    """Main orchestrator for the voice-to-code system"""

    def __init__(self, transcription_method=TranscriptionMethod.LOCAL_WHISPER, llm_method=LLMMethod.GEMINI,
                 debug=False, transcript_only=False, audio_source=AudioSource.BOTH, silence_timeout=1.0,
                 vad_aggressiveness=2,
                 generation_hotkey="ctrl+shift+g",
                 update_hotkey="ctrl+shift+s",
                 mode_switch_hotkey="ctrl+shift+m",
                 capture_hotkey="ctrl+shift+c",
                 edit_keyword="edit file",
                 close_keyword="close file",
                 coach_mode=False):
        self.audio_capture = AudioCapture(source=audio_source)
        self.edit_keyword = edit_keyword.lower()
        self.close_keyword = close_keyword.lower()
        self.generation_hotkey = generation_hotkey
        self.update_hotkey = update_hotkey
        self.mode_switch_hotkey = mode_switch_hotkey
        self.capture_hotkey = capture_hotkey
        self.debug = debug
        self.transcript_only = transcript_only
        self.audio_source = audio_source
        self.coach_mode = coach_mode
        self.llm_method = llm_method

        # Live transcript buffer for manual capture
        self.live_transcript_buffer = []

        # Spinner for listening indicator
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0

        self.vad_mic = VoiceActivityDetector(aggressiveness=vad_aggressiveness, sample_rate=16000)
        self.vad_system = VoiceActivityDetector(aggressiveness=vad_aggressiveness, sample_rate=48000)

        self.transcriber = SpeechTranscriber(method=transcription_method)

        # Initialize appropriate mode
        if coach_mode:
            self.interview_coach = InterviewCoach()
            self.code_generator = None
        elif not transcript_only:
            self.code_generator = CodeGenerator(llm_method=llm_method)
            self.interview_coach = None
        else:
            self.code_generator = None
            self.interview_coach = None

        self.silence_timeout = silence_timeout
        # Recalculate based on chunk size and sample rate (approximate)
        self.silence_chunks_needed = int(silence_timeout / (8192 / 16000))

        if debug:
            print(f"🔇 Silence timeout: {silence_timeout}s ({self.silence_chunks_needed} chunks)")
            print(f"🎯 WebRTC VAD aggressiveness: {vad_aggressiveness} (1-3, where 3 is most aggressive)")

        self.mic_buffer = deque(maxlen=200)
        self.system_buffer = deque(maxlen=200)
        self.is_running = False
        self.transcription_in_progress = False  # Track if transcription is currently running
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True)

        self.mic_speech_detected = False
        self.system_speech_detected = False
        self.mic_silence_counter = 0
        self.system_silence_counter = 0
        self.mic_speech_counter = 0
        self.system_speech_counter = 0

        self.max_speech_chunks = 200
        self.min_speech_chunks = 3

        # Command file for remote triggering from centralized config
        self.command_file = COMMAND_FILE
        self.last_command_check = 0
        self.command_check_interval = 0.5  # Check every 0.5 seconds

        # Control when listening starts
        self.listening_enabled = False

        if debug and not self.transcript_only:
            print(f"🗣️  Edit keyword: '{self.edit_keyword} [filename]'")
            print(f"⏹️  Close keyword: '{self.close_keyword}'")
            print(f"⌨️  New File Hotkey: {self.generation_hotkey}")
            print(f"💾 Update File Hotkey: {self.update_hotkey}")

    def check_remote_commands(self):
        """Check for remote commands from web/electron interface"""
        current_time = time.time()

        # Only check at specified interval
        if current_time - self.last_command_check < self.command_check_interval:
            return

        self.last_command_check = current_time

        # Check if command file exists
        if not self.command_file.exists():
            return

        try:
            # Read command
            command_text = self.command_file.read_text().strip()

            # Delete command file immediately
            self.command_file.unlink()

            # Try to parse as JSON (for commands with parameters)
            print(f"DEBUG: Raw command_text from file: '{command_text}'") # Added debug log
            try:
                import json
                command_data = json.loads(command_text)
                command = command_data.get("command", command_text)
            except (json.JSONDecodeError, ValueError):
                # Not JSON, treat as simple string command
                command = command_text
                command_data = {}

            # Execute command
            if command == "generate":
                print(f"\n🌐 Remote Generate command received!")
                self.on_generate_hotkey_press()
            elif command == "update":
                print(f"\n🌐 Remote Update command received!")
                self.on_update_hotkey_press()
            elif command == "toggle_mode":
                print(f"\n🌐 Remote Mode Toggle command received!")
                self.toggle_mode()
                print(f"DEBUG: toggle_mode() function completed.") # Added debug log
            elif command == "capture_transcript":
                print(f"\n🌐 Remote Capture Transcript command received!")
                self.capture_transcript_segment()
            elif command == "ui_capture_screenshot":
                print(f"\n🌐 Remote UI Screenshot Capture command received!")
                self.trigger_ui_screenshot()
            elif command == "analyze_screenshot":
                prompt = command_data.get("prompt", "What is this?")
                screenshot_path = command_data.get("screenshot_path")
                print(f"\n🖼️  Remote Analyze Screenshot command received!")
                if screenshot_path:
                    self.analyze_screenshot_with_gemini_cli(prompt, screenshot_path)
            elif command == "analyze_text_prompt":
                prompt = command_data.get("prompt", "No prompt provided.")
                print(f"\n💬 Remote Analyze Text Prompt command received!")
                if prompt:
                    self.analyze_text_with_gemini(prompt)

        except Exception as e:
            # Silently ignore errors (file might be deleted by another process)
            pass

    def trigger_ui_screenshot(self):
        """Sends a command to the web server to trigger a screenshot in the UI."""
        try:
            print("📡 Relaying command to web server to trigger UI screenshot...")
            # This is a simple fire-and-forget POST request.
            # The web_server will broadcast the command to all connected WebSocket clients.
            req = urllib.request.Request('http://localhost:5000/api/broadcast/command', 
                                         data=b'{"command": "capture_screenshot"}',
                                         headers={'Content-Type': 'application/json'},
                                         method='POST')
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    print("✅ Command successfully relayed to web server.")
                else:
                    print(f"⚠️  Web server responded with status: {response.status}")
        except Exception as e:
            print(f"❌ Failed to send trigger to web server: {e}")
            print("   Is the web server running? You can start it with: python web_server.py")

    def on_generate_hotkey_press(self):
        """Called to generate a NEW file, starting a fresh session."""
        print(f"\n⌨️  New File Hotkey pressed! Generating new file...")
        if not self.code_generator: return

        # Start listening if not already enabled
        if not self.listening_enabled:
            self.listening_enabled = True
            print("🎙️  Starting audio capture...")
            self.audio_capture.start_capture(
                mic_callback=self.mic_audio_callback if self.audio_source in [AudioSource.MICROPHONE, AudioSource.BOTH] else None,
                system_callback=self.system_audio_callback if self.audio_source in [AudioSource.SYSTEM, AudioSource.BOTH] else None
            )

        try:
            # If speech is currently being detected, force process it immediately
            if self.mic_speech_detected and len(self.mic_buffer) >= self.min_speech_chunks:
                print("⏳ Finalizing current speech segment...")
                self.process_speech_segment(source="You")
                self.mic_speech_detected = False
                self.mic_silence_counter = 0
                self.mic_speech_counter = 0

            if self.system_speech_detected and len(self.system_buffer) >= self.min_speech_chunks:
                print("⏳ Finalizing current speech segment...")
                self.process_speech_segment(source="Partner")
                self.system_speech_detected = False
                self.system_silence_counter = 0
                self.system_speech_counter = 0

            # Wait for any in-progress transcription to complete
            if self.transcription_in_progress:
                print("⏳ Waiting for transcription to complete...")
                max_wait = 10  # Wait up to 10 seconds
                for _ in range(max_wait * 10):
                    if not self.transcription_in_progress:
                        break
                    time.sleep(0.1)

            # Clear any active file to ensure we create a NEW file (not update existing)
            self.code_generator.active_file_path = None

            # Generate code with current context
            self.code_generator.generate_code_from_context()

            # Note: Context is NOT cleared here - it persists for refinement
            # Use "close file" voice command to explicitly clear context when starting fresh
        except Exception as e:
            print(f"❌ Error in generate hotkey callback: {e}")
            import traceback
            traceback.print_exc()

    def on_update_hotkey_press(self):
        """Called to UPDATE the active file."""
        print(f"\n💾 Update Hotkey pressed! Triggering file update...")
        if not self.code_generator: return

        if not self.code_generator.active_file_path:
            print("⚠️  No active file to update. Use 'edit file [filename]' to select one first.")
            return

        try:
            # If speech is currently being detected, force process it immediately
            if self.mic_speech_detected and len(self.mic_buffer) >= self.min_speech_chunks:
                print("⏳ Finalizing current speech segment...")
                self.process_speech_segment(source="You")
                self.mic_speech_detected = False
                self.mic_silence_counter = 0
                self.mic_speech_counter = 0

            if self.system_speech_detected and len(self.system_buffer) >= self.min_speech_chunks:
                print("⏳ Finalizing current speech segment...")
                self.process_speech_segment(source="Partner")
                self.system_speech_detected = False
                self.system_silence_counter = 0
                self.system_speech_counter = 0

            # Wait for any in-progress transcription to complete
            if self.transcription_in_progress:
                print("⏳ Waiting for transcription to complete...")
                max_wait = 10  # Wait up to 10 seconds
                for _ in range(max_wait * 10):
                    if not self.transcription_in_progress:
                        break
                    time.sleep(0.1)

            # The hotkey is the trigger, it shouldn't be part of the context.
            self.code_generator.generate_code_from_context()
        except Exception as e:
            print(f"❌ Error in update hotkey callback: {e}")
            import traceback
            traceback.print_exc()

    def send_coach_suggestions(self, question: str, suggestions: list, status: str = "completed"):
        """Send coaching suggestions to web server for overlay display"""
        # Write to file for web server to pick up
        coach_file = Path("generated_code") / ".coach_suggestions"
        try:
            data = {
                "question": question,
                "suggestions": suggestions,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            print(f"DEBUG: Writing to .coach_suggestions: {data}")
            coach_file.write_text(json.dumps(data, indent=2))
            print("DEBUG: Write to .coach_suggestions completed.")
        except Exception as e:
            print(f"⚠️  Failed to write coach suggestions: {e}")

    def send_transcript_segment(self, speaker: str, text: str):
        """Send transcript segment to web server for overlay display"""
        # Write to file for web server to pick up
        transcript_file = Path("generated_code") / ".transcript"
        try:
            import json
            data = {
                "speaker": speaker,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
            transcript_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"⚠️  Failed to write transcript segment: {e}")

    def send_live_transcript_buffer(self):
        """Send live transcript buffer to overlay for real-time display"""
        buffer_file = Path("generated_code") / ".live_transcript"
        try:
            import json
            data = {
                "buffer": self.live_transcript_buffer,
                "timestamp": datetime.now().isoformat()
            }
            buffer_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"⚠️  Failed to write live transcript buffer: {e}")

    def capture_transcript_segment(self):
        """Capture current live buffer as a permanent segment"""
        if not self.live_transcript_buffer:
            print("\n📋 No transcript to capture!")
            return

        # Combine all buffer items into a single segment
        combined_text = " ".join([item["text"] for item in self.live_transcript_buffer])
        # Use the speaker from the most recent item (or could be majority vote)
        speaker = self.live_transcript_buffer[-1]["speaker"] if self.live_transcript_buffer else "Unknown"

        print(f"\n📌 Capturing transcript segment ({len(combined_text)} chars)...")

        # Send as a captured segment
        self.send_transcript_segment(speaker, combined_text)

        # Save to history for MCP server
        self.save_transcript_to_history(speaker, combined_text)

        # Clear the live buffer
        self.live_transcript_buffer.clear()
        self.send_live_transcript_buffer()  # Update overlay to show empty buffer

    def save_transcript_to_history(self, speaker: str, text: str):
        """Save transcript segment to history file for MCP server access"""
        history_file = GENERATED_CODE_DIR / ".transcript_history"
        try:
            import json
            # Load existing history
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []

            # Add new segment
            history.append({
                "speaker": speaker,
                "text": text,
                "timestamp": datetime.now().isoformat()
            })

            # Save updated history
            history_file.write_text(json.dumps(history, indent=2))
        except Exception as e:
            print(f"⚠️  Failed to save transcript to history: {e}")

    def toggle_mode(self):
        """Toggle between Code Generation mode and Interview Coach mode"""
        print(f"\n🔄 Toggling mode...")

        # Toggle the mode flag
        self.coach_mode = not self.coach_mode

        if self.coach_mode:
            # Switching to Coach Mode
            print("🎯 Switching to Interview Coach Mode...")
            self.code_generator = None
            self.interview_coach = InterviewCoach()
            mode_name = "Coach"

            # Start audio capture if not already listening
            if not self.listening_enabled:
                self.listening_enabled = True
                print("🎙️  Starting audio capture for coach mode...")
                self.audio_capture.start_capture(
                    mic_callback=self.mic_audio_callback if self.audio_source in [AudioSource.MICROPHONE, AudioSource.BOTH] else None,
                    system_callback=self.system_audio_callback if self.audio_source in [AudioSource.SYSTEM, AudioSource.BOTH] else None
                )
        else:
            # Switching to Code Generation Mode
            print("💻 Switching to Code Generation Mode...")
            self.interview_coach = None
            self.code_generator = CodeGenerator(llm_method=self.llm_method)
            mode_name = "Code"

        # Notify web server of mode change
        mode_file = GENERATED_CODE_DIR / ".current_mode"
        try:
            data = {
                "mode": mode_name,
                "timestamp": datetime.now().isoformat()
            }
            mode_file.write_text(json.dumps(data, indent=2))
            print(f"DEBUG: Wrote to .current_mode file: {mode_file.name} with content: {json.dumps(data, indent=2)}") # Added debug log
        except Exception as e:
            print(f"⚠️  Failed to write mode change: {e}")

        print(f"✅ Now in {mode_name} Mode")

    def _perform_gemini_analysis_in_thread(self, prompt: str, image_path_obj: Path):
        """
        Helper function to run the blocking Gemini API call in a separate thread.
        """
        print("DEBUG: _perform_gemini_analysis_in_thread started")
        
        try:
            # --- This logic is now inside the thread ---
            model_to_use = None
            if self.coach_mode and self.interview_coach and self.interview_coach.gemini_model:
                model_to_use = self.interview_coach.gemini_model
            else:
                temp_coach = InterviewCoach()
                model_to_use = temp_coach.gemini_model
            print("DEBUG: Gemini model loaded")

            if not model_to_use:
                raise ValueError("Gemini model could not be initialized.")

            print("DEBUG: Loading image")
            import PIL.Image

            img = PIL.Image.open(image_path_obj)

            print("🤖 Calling Gemini API for analysis (in thread)...")
            response = model_to_use.generate_content([prompt, img])
            print("✅ Received response from Gemini API.")

            if response and hasattr(response, 'text') and response.text:

                analysis = response.text.strip()
                print(f"✅ Gemini Analysis Received:\n{analysis}")
                self.send_coach_suggestions(prompt, analysis.split('\n'))
            else:
                analysis = "Gemini did not return any text analysis. The response might be empty or blocked."
                print(f"❌ {analysis}")
                self.send_coach_suggestions(prompt, [analysis])
            print("DEBUG: _perform_gemini_analysis_in_thread completed successfully")

        except genai.types.generation_types.BlockedPromptException as e:
            error_message = f"Gemini API request was blocked. Reason: {e}"
            print(f"❌ {error_message}")
            self.send_coach_suggestions(prompt, [error_message])
            print("DEBUG: _perform_gemini_analysis_in_thread completed with BlockedPromptException")
        except Exception as e:
            error_message = f"An unexpected error occurred during screenshot analysis: {e}"
            print(f"❌ {error_message}")
            import traceback
            traceback.print_exc()
            self.send_coach_suggestions(prompt, [error_message])
            print("DEBUG: _perform_gemini_analysis_in_thread completed with Exception")


    def analyze_screenshot_with_gemini_cli(self, prompt: str, image_path: str): # Renaming this would be a good refactor, but let's keep it for now to minimize changes.
        """
        Analyzes a screenshot using the Gemini Python library.
        Displays the result in the coach suggestions panel.
        """
        print(f"🤖 Analyzing screenshot '{Path(image_path).name}' with Gemini API...")
        print(f"   Prompt: \"{prompt}\"")

        print("DEBUG: Calling send_coach_suggestions with status='loading'")
        # Immediately send a loading state to the UI
        self.send_coach_suggestions(prompt, ["Analyzing with Gemini..."], status="loading")
        print("DEBUG: send_coach_suggestions with status='loading' completed")

        try:
            print("DEBUG: Entering try block in analyze_screenshot_with_gemini_cli")

            # Ensure the image path is valid
            image_path_obj = Path(image_path)
            if not image_path_obj.exists():
                print(f"❌ Screenshot file not found at: {image_path}")
                self.send_coach_suggestions(prompt, [f"Error: Screenshot file not found at {image_path}"])
                return

            # --- Run the blocking API call in a separate thread ---
            analysis_thread = threading.Thread(
                target=self._perform_gemini_analysis_in_thread, args=(prompt, image_path_obj)
            )
            print("DEBUG: Starting analysis thread")
            analysis_thread.start()
            print("DEBUG: Analysis thread started")

        except Exception as e:
            error_message = f"An unexpected error occurred during screenshot analysis: {e}"
            print(f"❌ {error_message}")
            import traceback
            traceback.print_exc() # Print full traceback for unexpected errors
            print("DEBUG: Calling send_coach_suggestions with error message")
            self.send_coach_suggestions(prompt, [error_message])
            print("DEBUG: send_coach_suggestions with error message completed")

        finally:
            print("DEBUG: Exiting analyze_screenshot_with_gemini_cli")

    def analyze_text_with_gemini(self, prompt: str):
        """
        Analyzes a text prompt using the Gemini Python library and displays the result.
        This is a simplified version of the screenshot analysis for text-only input.
        """
        print(f"🤖 Analyzing text prompt with Gemini API...")
        print(f"   Prompt: \"{prompt}\"")

        # Immediately send a loading state to the UI
        self.send_coach_suggestions(prompt, ["Analyzing with Gemini..."], status="loading")

        # Run the analysis in a separate thread to avoid blocking
        analysis_thread = threading.Thread(target=self._perform_gemini_text_analysis_in_thread, args=(prompt,))
        analysis_thread.start()

    def mic_audio_callback(self, audio_chunk):
        """Called for each microphone audio chunk"""
        if not self.is_running: return False
        has_speech = self.vad_mic.is_speech(audio_chunk)
        if has_speech:
            self.mic_speech_detected = True
            self.mic_silence_counter = 0
            self.mic_speech_counter += 1
            self.mic_buffer.append(audio_chunk)
            if self.mic_speech_counter > self.max_speech_chunks:
                self.process_speech_segment(source="You")
                self.mic_speech_detected = False; self.mic_silence_counter = 0; self.mic_speech_counter = 0
        elif self.mic_speech_detected:
            self.mic_silence_counter += 1
            self.mic_buffer.append(audio_chunk)
            if self.mic_silence_counter > self.silence_chunks_needed:
                if self.mic_speech_counter >= self.min_speech_chunks:
                    self.process_speech_segment(source="You")
                self.mic_speech_detected = False; self.mic_silence_counter = 0; self.mic_speech_counter = 0
        return True

    def _perform_gemini_text_analysis_in_thread(self, prompt: str):
        """
        Helper function to run the blocking Gemini API call for text in a separate thread.
        """
        try:
            model_to_use = None
            if self.coach_mode and self.interview_coach and self.interview_coach.gemini_model:
                model_to_use = self.interview_coach.gemini_model
            else:
                temp_coach = InterviewCoach()
                model_to_use = temp_coach.gemini_model

            if not model_to_use:
                raise ValueError("Gemini model could not be initialized for text analysis.")

            print("🤖 Calling Gemini API for text analysis (in thread)...")
            response = model_to_use.generate_content(prompt)
            print("✅ Received response from Gemini API.")

            if response and hasattr(response, 'text') and response.text:
                analysis = response.text.strip()
                self.send_coach_suggestions(prompt, analysis.split('\n'))
            else:
                analysis = "Gemini did not return any text analysis."
                self.send_coach_suggestions(prompt, [analysis])

        except Exception as e:
            error_message = f"An unexpected error occurred during text analysis: {e}"
            print(f"❌ {error_message}")
            import traceback
            traceback.print_exc()
            self.send_coach_suggestions(prompt, [error_message])

    def process_transcript_for_commands(self, transcript_text: str):
        """Check transcript for keywords to edit or close a file."""
        lower_transcript = transcript_text.lower()

        # Check for "edit file" command
        if self.edit_keyword in lower_transcript:
            try:
                # Assumes command is "edit file my_file.py"
                filename = lower_transcript.split(self.edit_keyword)[1].strip().split()[0]
                if filename and self.code_generator:
                    print(f"\n📝 Edit command detected for file: '{filename}'")
                    self.code_generator.set_active_file(filename)
            except IndexError:
                print(f"⚠️  '{self.edit_keyword}' detected, but no filename was found.")
            return

        # Check for "close file" command
        if self.close_keyword in lower_transcript:
            print(f"\n⏹️  Close file command detected.")
            if self.code_generator:
                self.code_generator.close_active_file()
            return
        return True

    def system_audio_callback(self, audio_chunk):
        """Called for each system audio chunk"""
        if not self.is_running: return False

        # Show rotating spinner
        print(f"\r{self.spinner_chars[self.spinner_index]} Listening...", end="", flush=True)
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)

        has_speech = self.vad_system.is_speech(audio_chunk)
        if has_speech:
            self.system_speech_detected = True
            self.system_silence_counter = 0
            self.system_speech_counter += 1
            self.system_buffer.append(audio_chunk)
            if self.system_speech_counter > self.max_speech_chunks:
                self.process_speech_segment(source="Partner")
                self.system_speech_detected = False; self.system_silence_counter = 0; self.system_speech_counter = 0
        elif self.system_speech_detected:
            self.system_silence_counter += 1
            self.system_buffer.append(audio_chunk)
            if self.system_silence_counter > self.silence_chunks_needed:
                if self.system_speech_counter >= self.min_speech_chunks:
                    self.process_speech_segment(source="Partner")
                self.system_speech_detected = False; self.system_silence_counter = 0; self.system_speech_counter = 0
        return True

    def process_speech_segment(self, source="Unknown"):
        """Transcribe speech and add it to the conversation context."""
        buffer = self.mic_buffer if source == "You" else self.system_buffer
        if not buffer: return

        icon = "🎤" if source == "You" else "🔊"
        print(f"\n\n{icon} Processing speech from {source}...")

        # Mark transcription as in progress
        self.transcription_in_progress = True

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_file = self.temp_dir / f"speech_{source}_{timestamp}.wav"

        try:
            audio_data = b"".join(buffer)
            sample_rate = 16000
            if source == "Partner":
                audio_array = np.frombuffer(audio_data, dtype=np.int16).reshape(-1, 2).mean(axis=1).astype(np.int16)
                audio_data = audio_array[::3].tobytes() # Downsample 48kHz to 16kHz

            with wave.open(str(temp_file), "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate); wf.writeframes(audio_data)

            buffer.clear()
            transcript = self.transcriber.transcribe_audio(str(temp_file))

            if transcript:
                labeled_transcript = f"[{source}]: {transcript}"

                # Add to live transcript buffer
                self.live_transcript_buffer.append({
                    "speaker": source,
                    "text": transcript,
                    "timestamp": datetime.now().isoformat()
                })
                # Send updated buffer to overlay
                self.send_live_transcript_buffer()

                if self.transcript_only:
                    print(f"\n📝 {labeled_transcript}")
                elif self.coach_mode:
                    # Coach mode: Generate suggestions when interviewer speaks
                    print(f"\n📝 {labeled_transcript}")

                    if source == "Partner":  # Interviewer question
                        self.interview_coach.add_to_conversation("Interviewer", transcript)
                        suggestions = self.interview_coach.generate_suggestions(transcript)

                        # Display suggestions to console
                        print("\n💡 Suggested Response:")
                        for i, suggestion in enumerate(suggestions, 1):
                            print(f"   {i}. {suggestion}")

                        # Send to web server for overlay display
                        self.send_coach_suggestions(transcript, suggestions)
                    else:  # Candidate response
                        self.interview_coach.add_to_conversation("You", transcript)
                else:
                    # Code generation mode
                    # Always add the full transcript to context first
                    self.code_generator.update_context(labeled_transcript)

                    # Then, check for keyword commands in the transcript
                    self.process_transcript_for_commands(transcript)

        finally:
            if temp_file.exists(): temp_file.unlink()
            # Mark transcription as complete
            self.transcription_in_progress = False

    def start(self):
        """Start the voice-to-code system"""
        print("\n" + "="*60)
        if self.coach_mode:
            print("🎯 INTERVIEW COACH MODE")
        elif self.transcript_only:
            print("🚀 TRANSCRIPT-ONLY MODE")
        else:
            print("🚀 CONTEXT-AWARE VOICE-TO-CODE SYSTEM")
        print("="*60)

        # Show audio sources
        if self.audio_source == AudioSource.BOTH:
            print("\n🎧 Dual Audio Mode: [You] (mic) and [Partner] (system audio)")
        else:
            print(f"\n🎧 Single Audio Mode: {self.audio_source.value}")

        if self.coach_mode:
            print("\n💡 Interview Coach will provide real-time suggestions for interviewer questions.")
            print("\n📋 System will listen to the interview and generate tactical response guidance.")
            print("   - Interviewer questions → AI generates talking points")
            print("   - Your responses → Tracked for context")
            print("   - Suggestions appear in console and overlay")
        elif self.transcript_only:
            print("\n📋 System will transcribe and display conversation in real-time.")
            print("\n💡 Code generation is DISABLED.")
        else:
            print("\n📋 System will continuously listen and build conversation context.")
            print("\n🎯 CONTROLS:")
            print(f"   - Say '{self.edit_keyword} [filename]' to start editing.")
            print(f"   - Say '{self.close_keyword}' to stop editing.")
            print(f"   - Press {self.generation_hotkey} to generate a NEW file.")
            print(f"   - Press {self.update_hotkey} to SAVE changes to the active file.")


        print("\n⏹️  Press Ctrl+C to stop\n")
        self.is_running = True

        try:
            # Register keyboard hotkeys if needed
            if not self.transcript_only and KEYBOARD_AVAILABLE:
                try:
                    # Code generation hotkeys (only if not in coach mode)
                    if not self.coach_mode:
                        keyboard.add_hotkey(self.generation_hotkey, self.on_generate_hotkey_press)
                        print(f"✅ Hotkey '{self.generation_hotkey}' registered for new files.")
                        keyboard.add_hotkey(self.update_hotkey, self.on_update_hotkey_press)
                        print(f"✅ Hotkey '{self.update_hotkey}' registered for updating files.")

                    # Mode switch hotkey (always available)
                    keyboard.add_hotkey(self.mode_switch_hotkey, self.toggle_mode)
                    print(f"✅ Hotkey '{self.mode_switch_hotkey}' registered for mode switching.")

                    # Capture transcript hotkey (always available)
                    keyboard.add_hotkey(self.capture_hotkey, self.capture_transcript_segment)
                    print(f"✅ Hotkey '{self.capture_hotkey}' registered for capturing transcript.\n")
                except Exception as e:
                    print(f"⚠️  Failed to register hotkeys: {e}\n")
            elif not self.transcript_only:
                 print(f"⚠️  Hotkeys disabled because 'keyboard' library not found.\n")

            # Start listening based on mode
            if self.transcript_only or self.coach_mode:
                # Transcript-only and coach mode start listening immediately
                self.listening_enabled = True
                self.audio_capture.start_capture(
                    mic_callback=self.mic_audio_callback if self.audio_source in [AudioSource.MICROPHONE, AudioSource.BOTH] else None,
                    system_callback=self.system_audio_callback if self.audio_source in [AudioSource.SYSTEM, AudioSource.BOTH] else None
                )
            else:
                # Code generation mode waits for trigger
                print("💤 Waiting for first trigger (New button or hotkey) to start listening...\n")

            while self.is_running:
                # Check for remote commands (mode toggle is always available)
                if not self.transcript_only:
                    self.check_remote_commands()
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping system...")
        finally:
            self.stop()

    def stop(self):
        """Stop the system"""
        self.is_running = False

        # Unhook keyboard hotkeys first
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
                time.sleep(0.1)  # Give keyboard threads time to cleanup
            except:
                pass

        # Stop audio capture
        self.audio_capture.cleanup()

        # Give threads time to fully terminate
        time.sleep(0.2)

        print("✅ System stopped")


def start_web_server():
    """Start the web server in a separate process"""
    try:
        # Check if web_server.py exists
        web_server_path = Path(__file__).parent / "web_server.py"
        if not web_server_path.exists():
            print("⚠️  web_server.py not found. Web viewer will not be available.")
            return None

        # Check if port 5000 is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()

        if result == 0:
            print("⚠️  Port 5000 is already in use. Web viewer may already be running.")
            print(f"   If not, check http://localhost:5000\n")
            return None

        # Start web server in separate process using uv run to ensure proper environment
        # Note: On Windows, we don't use CREATE_NEW_PROCESS_GROUP so we can properly terminate it
        process = subprocess.Popen(
            ["uv", "run", "python", str(web_server_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Give it a moment to start
        time.sleep(1)

        print("🌐 Web viewer started at http://localhost:5000")
        print("   Open this URL in your browser to view generated code")
        print("   Press F9 in the browser to toggle semi-transparent overlay mode\n")

        return process

    except Exception as e:
        print(f"⚠️  Failed to start web server: {e}")
        print("   You can start it manually with: python web_server.py\n")
        return None


def main():
    """Main entry point"""

    # Fix Windows console encoding for emojis
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    # Enable logging to file
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_filename = log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    sys.stdout = Logger(log_filename)
    print(f"📄 Logging to: {log_filename}\n")

    # Start web server (if enabled via env var)
    web_server_process = None
    debug = False  # Initialize debug flag early
    enable_web_viewer = os.getenv("ENABLE_WEB_VIEWER", "true").lower() == "true"
    if enable_web_viewer:
        web_server_process = start_web_server()

    # Get transcription method from environment or default to local
    method_str = os.getenv("TRANSCRIPTION_METHOD", "local").lower()

    method_map = {
        "local": TranscriptionMethod.LOCAL_WHISPER,
        "openai": TranscriptionMethod.OPENAI_WHISPER,
        "groq": TranscriptionMethod.GROQ,
        "google": TranscriptionMethod.GOOGLE_CLOUD,
    }

    transcription_method = method_map.get(method_str, TranscriptionMethod.LOCAL_WHISPER)

    # Get LLM method from environment or default to Gemini
    llm_str = os.getenv("LLM_METHOD", "gemini").lower()

    llm_map = {
        "claude": LLMMethod.CLAUDE,
        "gemini": LLMMethod.GEMINI,
    }

    llm_method = llm_map.get(llm_str, LLMMethod.GEMINI)

    print(f"\n🎯 Transcription Method: {transcription_method.value.upper()}")
    print(f"🤖 LLM Method: {llm_method.value.upper()}")

    # Check for required API keys based on method
    if transcription_method == TranscriptionMethod.OPENAI_WHISPER:
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY not found in .env")
            print("💡 Add it to .env or switch to local: TRANSCRIPTION_METHOD=local")
            return

    if transcription_method == TranscriptionMethod.GOOGLE_CLOUD:
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
            print("💡 Set it to your JSON key file path or switch to local: TRANSCRIPTION_METHOD=local")
            return

    if llm_method == LLMMethod.CLAUDE:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("❌ ANTHROPIC_API_KEY not found in .env")
            print("💡 Add it to .env or switch to Gemini: LLM_METHOD=gemini")
            return
    elif llm_method == LLMMethod.GEMINI:
        if not os.getenv("GOOGLE_API_KEY"):
            print("❌ GOOGLE_API_KEY not found in .env")
            print("💡 Get a free API key at: https://aistudio.google.com/app/apikey")
            return

    # Check for debug mode, transcript-only mode, and coach mode
    debug = os.getenv("DEBUG", "false").lower() == "true"  # Read from env
    transcript_only = os.getenv("TRANSCRIPT_ONLY", "false").lower() == "true"
    coach_mode = os.getenv("COACH_MODE", "false").lower() == "true"

    # Get audio source configuration
    audio_source_str = os.getenv("AUDIO_SOURCE", "both").lower()
    audio_source_map = {
        "microphone": AudioSource.MICROPHONE,
        "mic": AudioSource.MICROPHONE,
        "system": AudioSource.SYSTEM,
        "both": AudioSource.BOTH,
    }
    audio_source = audio_source_map.get(audio_source_str, AudioSource.BOTH)

    # Get silence timeout from environment (default 1.0 second)
    try:
        silence_timeout = float(os.getenv("SILENCE_TIMEOUT", "1.0"))
    except ValueError:
        silence_timeout = 1.0

    # Get VAD aggressiveness from environment (default 2, range 1-3)
    try:
        vad_aggressiveness = int(os.getenv("VAD_AGGRESSIVENESS", "2"))
        # Clamp to valid range
        vad_aggressiveness = max(1, min(3, vad_aggressiveness))
    except ValueError:
        vad_aggressiveness = 2

    # Get trigger mode configuration for code generation
    generation_hotkey = os.getenv("GENERATION_HOTKEY", "ctrl+shift+g")
    update_hotkey = os.getenv("UPDATE_HOTKEY", "ctrl+shift+s")
    mode_switch_hotkey = os.getenv("MODE_SWITCH_HOTKEY", "ctrl+shift+m")
    capture_hotkey = os.getenv("CAPTURE_HOTKEY", "ctrl+shift+c")
    edit_keyword = os.getenv("EDIT_KEYWORD", "edit file")
    close_keyword = os.getenv("CLOSE_KEYWORD", "close file")


    if debug:
        print(f"🎧 Audio Source: {audio_source.value.upper()}")

    # Start the system
    try:
        system = VoiceToCodeSystem(
            transcription_method=transcription_method,
            llm_method=llm_method,
            debug=debug,
            transcript_only=transcript_only,
            audio_source=audio_source,
            silence_timeout=silence_timeout,
            vad_aggressiveness=vad_aggressiveness,
            generation_hotkey=generation_hotkey,
            update_hotkey=update_hotkey,
            mode_switch_hotkey=mode_switch_hotkey,
            capture_hotkey=capture_hotkey,
            edit_keyword=edit_keyword,
            close_keyword=close_keyword,
            coach_mode=coach_mode
        )
        system.start()
    except Exception as e:
        print(f"\n❌ Failed to start system: {e}")
        print("\n💡 Tip: For completely FREE setup:")
        print("   1. Get Gemini API key: https://aistudio.google.com/app/apikey")
        print("   2. Set in .env: GOOGLE_API_KEY=your_key_here")
        print("   3. Set in .env: LLM_METHOD=gemini")
        print("   4. Set in .env: TRANSCRIPTION_METHOD=local")
        print("\n💡 Tip: If audio isn't being detected:")
        print("   1. Set in .env: DEBUG=true")
        print("   2. Check the energy levels shown")
        print("   3. Adjust volume or threshold if needed")
    finally:
        # Clean up web server process
        if web_server_process:
            try:
                if debug:
                    print("\n🧹 Cleaning up web server...")
                web_server_process.terminate()
                try:
                    web_server_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if terminate didn't work
                    web_server_process.kill()
                    web_server_process.wait(timeout=1)
                if debug:
                    print("✅ Web server stopped")
            except Exception as e:
                if debug:
                    print(f"⚠️  Error cleaning up web server: {e}")


if __name__ == "__main__":
    main()
