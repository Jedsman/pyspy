"""
Quick test script for the voice-to-code system
Tests individual components without needing audio capture
"""

import os
import sys
from dotenv import load_dotenv
from voice_to_code import CodeGenerator, TranscriptionMethod, LLMMethod
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

def test_llm_connection():
    """Test if LLM API key works (Gemini or Claude)"""
    llm_method = os.getenv("LLM_METHOD", "gemini").lower()

    if llm_method == "gemini":
        print("\n🧪 Testing Gemini API connection...")
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
            model = genai.GenerativeModel(model_name)

            response = model.generate_content("Say 'API connection successful!' and nothing else.")
            print(f"✅ {model_name} API works! Response: {response.text}")
            return True
        except Exception as e:
            print(f"❌ Gemini API failed: {e}")
            return False
    else:
        print("\n🧪 Testing Anthropic API connection...")
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            # Simple test message
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=100,
                messages=[{"role": "user", "content": "Say 'API connection successful!' and nothing else."}]
            )

            response = message.content[0].text
            print(f"✅ Anthropic API works! Response: {response}")
            return True

        except Exception as e:
            print(f"❌ Anthropic API failed: {e}")
            return False


def test_code_generation():
    """Test the code generator with a sample conversation"""
    print("\n🧪 Testing code generation...")

    try:
        # Get LLM method from environment
        llm_method_str = os.getenv("LLM_METHOD", "gemini").lower()
        llm_method = LLMMethod.GEMINI if llm_method_str == "gemini" else LLMMethod.CLAUDE

        generator = CodeGenerator(llm_method=llm_method)

        # Simulate a programming conversation
        test_conversation = """
        User: Let's create a Python function that validates email addresses using regex.
        Partner: Good idea. Make sure it handles common edge cases like dots and plus signs.
        User: Yeah, and let's add some basic tests too.
        """

        print(f"📝 Test conversation:\n{test_conversation}")
        print(f"\n🤖 Sending to {llm_method.value.upper()} for code generation...")

        generator.process_transcript(test_conversation)

        print("✅ Code generation test complete!")
        print("💡 Check the 'generated_code/' folder for output")
        return True

    except Exception as e:
        print(f"❌ Code generation failed: {e}")
        return False


def test_whisper_availability():
    """Check if Whisper is installed"""
    print("\n🧪 Checking Whisper installation...")

    method = os.getenv("TRANSCRIPTION_METHOD", "local").lower()

    if method == "local":
        try:
            import whisper
            print("✅ Local Whisper is installed")
            print("💡 To test transcription, you'll need to run the full system")
            return True
        except ImportError:
            print("❌ Local Whisper not installed")
            print("💡 Run: uv sync --extra local")
            return False
    elif method == "openai":
        if os.getenv("OPENAI_API_KEY"):
            print("✅ OpenAI API key found")
            return True
        else:
            print("❌ OPENAI_API_KEY not set")
            return False
    elif method == "google":
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            print("✅ Google credentials found")
            return True
        else:
            print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
            return False


def main():
    print("="*60)
    print("🧪 VOICE-TO-CODE SYSTEM TEST")
    print("="*60)

    results = []

    # Test 1: LLM API connection
    results.append(("LLM API", test_llm_connection()))

    # Test 2: Whisper availability
    results.append(("Transcription Setup", test_whisper_availability()))

    # Test 3: Code generation
    results.append(("Code Generation", test_code_generation()))

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\n💡 Next steps:")
        print("   1. Run: uv run voice_to_code.py")
        print("   2. Play a YouTube video about programming")
        print("   3. Watch it transcribe and generate code!")
    else:
        print("\n⚠️  Some tests failed. Fix the issues above and try again.")

    return all_passed


if __name__ == "__main__":
    main()
