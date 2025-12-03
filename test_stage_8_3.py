"""
Stage 8.3: Cross-Mode Stability Testing
Tests LLM mode switching and configuration persistence
"""

import os
import sys
from llm_router import get_router, GeminiRouter, ClaudeRouter


def test_mode_detection():
    """Test 8.3.1: LLM Mode Detection from Environment"""
    print("\n=== Test 8.3.1: Mode Detection ===")
    
    # Test current mode
    current_mode = os.getenv("LLM_METHOD", "gemini").lower()
    print(f"[PASS] Current LLM_METHOD: {current_mode}")
    
    # Test that mode is recognized
    valid_modes = ["gemini", "claude"]
    assert current_mode in valid_modes, f"Invalid mode: {current_mode}"
    print(f"[PASS] Mode is recognized")
    
    return True


def test_router_switching():
    """Test 8.3.2: Router Switching"""
    print("\n=== Test 8.3.2: Router Switching ===")
    
    # Create Gemini router
    gemini_router = get_router("gemini", "Gemini system prompt")
    assert isinstance(gemini_router, GeminiRouter)
    assert gemini_router.get_name() == "Gemini"
    print(f"[PASS] Gemini router created")
    
    # Create Claude router
    claude_router = get_router("claude", "Claude system prompt")
    assert isinstance(claude_router, ClaudeRouter)
    assert claude_router.get_name() == "Claude"
    print(f"[PASS] Claude router created")
    
    # Verify they are different instances
    assert gemini_router is not claude_router, "Routers should be different instances"
    print(f"[PASS] Routers are independent instances")
    
    return True


def test_router_isolation():
    """Test 8.3.3: Router Isolation (No State Leakage)"""
    print("\n=== Test 8.3.3: Router Isolation ===")
    
    # Create first Gemini router with specific prompt
    router1 = get_router("gemini", "Prompt 1")
    
    # Create second Gemini router with different prompt
    router2 = get_router("gemini", "Prompt 2")
    
    # Verify prompts are separate
    assert router1.system_prompt == "Prompt 1", "Router1 prompt corrupted"
    assert router2.system_prompt == "Prompt 2", "Router2 prompt corrupted"
    print(f"[PASS] Router prompts are isolated")
    
    # Create Claude router
    router3 = get_router("claude", "Claude Prompt")
    
    # Verify Claude router has correct prompt
    assert router3.system_prompt == "Claude Prompt", "Claude router prompt corrupted"
    print(f"[PASS] Claude router maintains separate state")
    
    # Verify Gemini routers still have their prompts
    assert router1.system_prompt == "Prompt 1", "Router1 prompt lost"
    assert router2.system_prompt == "Prompt 2", "Router2 prompt lost"
    print(f"[PASS] No cross-router state leakage")
    
    return True


def test_router_api_key_validation():
    """Test 8.3.4: API Key Validation per Router"""
    print("\n=== Test 8.3.4: API Key Validation ===")
    
    # Gemini router should have Google API key
    gemini_router = get_router("gemini", "Test")
    google_key = os.getenv("GOOGLE_API_KEY")
    assert google_key, "GOOGLE_API_KEY not set"
    assert gemini_router.api_key is not None, "Gemini router missing API key"
    print(f"[PASS] Gemini router has API key")
    
    # Claude router should check for Anthropic API key
    claude_router = get_router("claude", "Test")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    # Claude router may warn but doesn't fail if key missing
    print(f"[PASS] Claude router created (key present: {bool(anthropic_key)})")
    
    return True


def test_router_factory_consistency():
    """Test 8.3.5: Router Factory Consistency"""
    print("\n=== Test 8.3.5: Router Factory Consistency ===")
    
    # Call factory multiple times for same backend
    router1 = get_router("gemini", "System 1")
    router2 = get_router("gemini", "System 2")
    router3 = get_router("gemini", "System 3")
    
    # All should be GeminiRouter instances
    assert all(isinstance(r, GeminiRouter) for r in [router1, router2, router3])
    print(f"[PASS] Factory consistently creates correct type")
    
    # All should have different system prompts
    prompts = [r.system_prompt for r in [router1, router2, router3]]
    assert len(set(prompts)) == 3, "Prompts should be unique"
    print(f"[PASS] Each router instance is independent")
    
    # Model should be consistent
    assert all(r.model for r in [router1, router2, router3])
    print(f"[PASS] All routers have model configured")
    
    return True


def test_invalid_mode_handling():
    """Test 8.3.6: Invalid Mode Handling"""
    print("\n=== Test 8.3.6: Invalid Mode Handling ===")
    
    try:
        invalid_router = get_router("invalid_mode", "Test")
        print(f"[FAIL] Should have raised ValueError for invalid mode")
        return False
    except ValueError as e:
        if "Unknown LLM method" in str(e):
            print(f"[PASS] Invalid mode correctly raises ValueError")
            return True
        else:
            print(f"[FAIL] Wrong error message: {e}")
            return False


def main():
    """Run all Stage 8.3 tests"""
    print("\n" + "="*60)
    print("STAGE 8.3: CROSS-MODE STABILITY TESTING")
    print("="*60)
    
    tests = [
        ("Mode Detection", test_mode_detection),
        ("Router Switching", test_router_switching),
        ("Router Isolation", test_router_isolation),
        ("API Key Validation", test_router_api_key_validation),
        ("Router Factory Consistency", test_router_factory_consistency),
        ("Invalid Mode Handling", test_invalid_mode_handling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
