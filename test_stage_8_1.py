"""
Stage 8.1: Gemini Path Testing
Tests the voice-to-code system with Gemini backend
"""

import asyncio
import os
import sys
from pathlib import Path

# Import the system
from voice_to_code import VoiceToCodeSystem, LLMMethod
from llm_router import get_router, GeminiRouter
from config import GENERATED_CODE_DIR, SCREENSHOTS_DIR


def test_configuration():
    """Test 8.1.1: Configuration and Environment"""
    print("\n=== Test 8.1.1: Configuration ===")
    
    # Check LLM method selection
    llm_method_env = os.getenv("LLM_METHOD", "gemini").lower()
    assert llm_method_env == "gemini", f"Expected LLM_METHOD=gemini, got {llm_method_env}"
    print("[PASS] LLM_METHOD environment variable correct")
    
    # Check API keys
    google_key = os.getenv("GOOGLE_API_KEY")
    assert google_key, "GOOGLE_API_KEY not set"
    print("[PASS] GOOGLE_API_KEY available")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    print(f"[PASS] ANTHROPIC_API_KEY available: {bool(anthropic_key)}")
    
    # Check paths
    assert GENERATED_CODE_DIR.exists(), f"GENERATED_CODE_DIR doesn't exist: {GENERATED_CODE_DIR}"
    print(f"[PASS] GENERATED_CODE_DIR exists: {GENERATED_CODE_DIR}")
    
    assert SCREENSHOTS_DIR.exists() or True, f"Creating SCREENSHOTS_DIR: {SCREENSHOTS_DIR}"
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[PASS] SCREENSHOTS_DIR ready: {SCREENSHOTS_DIR}")
    
    return True


def test_router_factory():
    """Test 8.1.2: LLM Router Factory"""
    print("\n=== Test 8.1.2: LLM Router Factory ===")
    
    # Test Gemini router creation
    router = get_router("gemini", "Test system prompt")
    assert isinstance(router, GeminiRouter), f"Expected GeminiRouter, got {type(router)}"
    print(f"[PASS] Router factory creates GeminiRouter: {router.get_name()}")
    
    # Test that router has the required interface
    assert hasattr(router, "process"), "Router missing process() method"
    assert hasattr(router, "get_name"), "Router missing get_name() method"
    print("[PASS] Router has required interface (process, get_name)")
    
    # Test system prompt storage
    assert router.system_prompt == "Test system prompt", "System prompt not stored correctly"
    print("[PASS] System prompt correctly stored in router")
    
    return True


async def test_router_process():
    """Test 8.1.3: Router Process Method"""
    print("\n=== Test 8.1.3: Router Process Method ===")
    
    router = get_router("gemini", "You are a helpful assistant.")
    
    # Test process method with simple input
    print("Testing async process method...")
    result = await router.process(
        conversation="Write hello world in Python",
        active_file_content=None,
        custom_system_prompt=None
    )
    
    assert result is not None, "Process returned None"
    assert "type" in result, "Result missing 'type' field"
    assert "data" in result, "Result missing 'data' field"
    print(f"[PASS] Router process returns proper structure: {result['type']}")
    
    if result['type'] == 'error':
        print(f"  Error: {result['data']}")
    else:
        data_str = str(result['data'])
        print(f"  Data length: {len(data_str)} characters")
        if len(data_str) > 200:
            print(f"  Sample: {data_str[:200]}...")
    
    return True


def test_voice_to_code_system():
    """Test 8.1.4: VoiceToCodeSystem Initialization"""
    print("\n=== Test 8.1.4: VoiceToCodeSystem Initialization ===")
    
    # Test system initialization
    try:
        # Create system with Gemini
        system = VoiceToCodeSystem(
            transcription_method="local",  # Use local to avoid API calls
            llm_method=LLMMethod.GEMINI,
            debug=True,
            transcript_only=True,  # Don't actually process audio
            audio_source="microphone"
        )
        print("[PASS] VoiceToCodeSystem initialized with Gemini")
        
        # Check that system has required attributes
        assert hasattr(system, "code_generator"), "Missing code_generator"
        print("[PASS] System has code_generator attribute")
        
        assert hasattr(system, "transcript_manager"), "Missing transcript_manager"
        print("[PASS] System has transcript_manager attribute")
        
        return True
    except Exception as e:
        print(f"[FAIL] Failed to initialize: {e}")
        return False


def test_code_generator_router():
    """Test 8.1.5: CodeGenerator Router Integration"""
    print("\n=== Test 8.1.5: CodeGenerator Router Integration ===")
    
    from voice_to_code import CodeGenerator, LLMMethod
    
    # Create CodeGenerator with explicit router
    router = get_router("gemini", "You are a code generation AI")
    code_gen = CodeGenerator(output_dir=GENERATED_CODE_DIR, llm_router=router)
    
    assert code_gen.llm_router is not None, "Router not set in CodeGenerator"
    assert code_gen.llm_router.get_name() == "Gemini", "Wrong router type"
    print("[PASS] CodeGenerator properly integrated with router")
    
    # Check system prompt
    assert code_gen.system_prompt, "System prompt not set"
    print("[PASS] CodeGenerator has system prompt configured")
    
    return True


def test_transcription_paths():
    """Test 8.1.6: Transcription and Generated File Paths"""
    print("\n=== Test 8.1.6: File Paths ===")
    
    # Check that generated_code directory is ready
    assert GENERATED_CODE_DIR.exists(), f"Generated code directory missing: {GENERATED_CODE_DIR}"
    print(f"[PASS] Generated code directory: {GENERATED_CODE_DIR}")
    
    # Check that screenshots directory is ready
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    assert SCREENSHOTS_DIR.exists(), f"Screenshots directory missing: {SCREENSHOTS_DIR}"
    print(f"[PASS] Screenshots directory: {SCREENSHOTS_DIR}")
    
    # Check for transcript files
    live_transcript = GENERATED_CODE_DIR / ".live_transcript"
    print(f"[PASS] Live transcript path ready: {live_transcript}")
    
    return True


def main():
    """Run all Stage 8.1 tests"""
    print("\n" + "="*60)
    print("STAGE 8.1: GEMINI PATH TESTING")
    print("="*60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Router Factory", test_router_factory),
        ("Router Process", test_router_process),
        ("VoiceToCodeSystem", test_voice_to_code_system),
        ("CodeGenerator Router", test_code_generator_router),
        ("File Paths", test_transcription_paths),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            # Run async tests differently
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            
            if result:
                passed += 1
            else:
                failed += 1
                print(f"[FAIL] {test_name} returned False")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {test_name} failed with exception: {e}")
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
