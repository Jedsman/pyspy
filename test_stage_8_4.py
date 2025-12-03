"""
Stage 8.4: Performance and Reliability Testing
Tests startup time, file operations, and graceful error handling
"""

import os
import sys
import time
from pathlib import Path
from llm_router import get_router


def test_startup_time():
    """Test 8.4.1: Startup Time"""
    print("\n=== Test 8.4.1: Startup Time ===")
    
    start = time.time()
    router = get_router("gemini", "Test")
    elapsed = time.time() - start
    
    print(f"[PASS] Router creation took {elapsed:.3f} seconds")
    assert elapsed < 1.0, f"Router creation too slow: {elapsed}s"
    print(f"[PASS] Within acceptable time (< 1s)")
    
    return True


def test_multiple_router_creation():
    """Test 8.4.2: Multiple Router Creation"""
    print("\n=== Test 8.4.2: Multiple Router Creation ===")
    
    start = time.time()
    routers = []
    for i in range(20):
        routers.append(get_router("gemini", f"Prompt {i}"))
    elapsed = time.time() - start
    
    print(f"[PASS] Created {len(routers)} routers in {elapsed:.3f} seconds")
    print(f"[PASS] Average time per router: {elapsed/len(routers)*1000:.2f}ms")
    
    # All routers should be valid
    for router in routers:
        assert router is not None
        assert router.get_name() == "Gemini"
    
    print(f"[PASS] All routers are valid")
    
    return True


def test_file_operations():
    """Test 8.4.3: File Operations Stability"""
    print("\n=== Test 8.4.3: File Operations ===")
    
    from config import GENERATED_CODE_DIR
    import json
    
    # Create multiple files
    files_created = []
    for i in range(10):
        test_file = GENERATED_CODE_DIR / f".test_file_{i}"
        test_file.write_text(json.dumps({"index": i, "data": "test"}))
        files_created.append(test_file)
    
    print(f"[PASS] Created {len(files_created)} test files")
    
    # Verify all files exist and are readable
    for test_file in files_created:
        assert test_file.exists(), f"File missing: {test_file}"
        data = json.loads(test_file.read_text())
        assert "index" in data, f"File corrupted: {test_file}"
    
    print(f"[PASS] All files readable and valid")
    
    # Cleanup
    for test_file in files_created:
        test_file.unlink()
    
    print(f"[PASS] Cleanup successful")
    
    return True


def test_large_data_handling():
    """Test 8.4.4: Large Data Handling"""
    print("\n=== Test 8.4.4: Large Data Handling ===")
    
    from config import GENERATED_CODE_DIR
    
    # Create large test data
    large_file = GENERATED_CODE_DIR / ".test_large"
    large_content = "x" * (5 * 1024 * 1024)  # 5MB
    
    large_file.write_text(large_content)
    assert large_file.exists()
    print(f"[PASS] Created 5MB file")
    
    # Read it back
    read_content = large_file.read_text()
    assert len(read_content) == len(large_content)
    print(f"[PASS] File integrity maintained")
    
    # Cleanup
    large_file.unlink()
    
    return True


def test_error_recovery():
    """Test 8.4.5: Error Recovery"""
    print("\n=== Test 8.4.5: Error Recovery ===")
    
    try:
        # Test invalid factory call
        try:
            bad_router = get_router("invalid", "Test")
            print(f"[FAIL] Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"[PASS] Factory correctly handles invalid mode")
        
        # System should still work after error
        good_router = get_router("gemini", "Test")
        assert good_router is not None
        print(f"[PASS] System recovers after error")
        
        # Create another router
        another_router = get_router("claude", "Test")
        assert another_router is not None
        print(f"[PASS] System works with different backend after error")
        
        return True
    except Exception as e:
        print(f"[FAIL] Error recovery failed: {e}")
        return False


def test_router_isolation_stress():
    """Test 8.4.6: Router Isolation Under Stress"""
    print("\n=== Test 8.4.6: Router Isolation Stress ===")
    
    # Create many routers with same model
    routers = []
    for i in range(50):
        router = get_router("gemini", f"System {i}")
        routers.append(router)
    
    # Verify isolation - random checks
    assert routers[0].system_prompt == "System 0"
    assert routers[25].system_prompt == "System 25"
    assert routers[49].system_prompt == "System 49"
    
    print(f"[PASS] Created 50 routers with perfect isolation")
    
    return True


def main():
    """Run all Stage 8.4 tests"""
    print("\n" + "="*60)
    print("STAGE 8.4: PERFORMANCE AND RELIABILITY TESTING")
    print("="*60)
    
    tests = [
        ("Startup Time", test_startup_time),
        ("Multiple Router Creation", test_multiple_router_creation),
        ("File Operations", test_file_operations),
        ("Large Data Handling", test_large_data_handling),
        ("Error Recovery", test_error_recovery),
        ("Router Isolation Stress", test_router_isolation_stress),
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
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
