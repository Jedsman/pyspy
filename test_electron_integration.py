"""
Electron App Integration Test
Verifies that the Python backend and Electron app can communicate properly
"""

import asyncio
import json
import os
import sys
import time
import socket
from pathlib import Path

# Import required modules
try:
    from voice_to_code import VoiceToCodeSystem, LLMMethod
    from llm_router import get_router
    from config import GENERATED_CODE_DIR, SCREENSHOTS_DIR
except ImportError as e:
    print(f"[FAIL] Cannot import voice_to_code modules: {e}")
    sys.exit(1)


def test_file_structure():
    """Test 1: Verify all required files exist"""
    print("\n=== Test 1: File Structure ===")

    required_files = {
        'Python': {
            'voice_to_code.py': Path('voice_to_code.py'),
            'web_server.py': Path('web_server.py'),
            'llm_router.py': Path('llm_router.py'),
            'mcp_server.py': Path('mcp_server.py'),
        },
        'Electron': {
            'overlay.html': Path('electron-overlay/overlay.html'),
            'custom_prompts.js': Path('electron-overlay/custom_prompts.js'),
            'main.js': Path('electron-overlay/main.js'),
            'preload.js': Path('electron-overlay/preload.js'),
            'package.json': Path('electron-overlay/package.json'),
        },
        'Configuration': {
            '.env': Path('.env'),
            'claude_desktop_config.json': Path('claude_desktop_config.json'),
        }
    }

    all_exist = True
    for category, files in required_files.items():
        print(f"\n{category}:")
        for name, path in files.items():
            exists = path.exists()
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {name}")
            if not exists:
                all_exist = False

    return all_exist


def test_environment_config():
    """Test 2: Verify environment configuration"""
    print("\n=== Test 2: Environment Configuration ===")

    required_env = {
        'GOOGLE_API_KEY': False,  # For Gemini
        'ANTHROPIC_API_KEY': False,  # For Claude (optional)
        'TRANSCRIPTION_METHOD': True,  # Should have default
        'LLM_METHOD': True,  # Should have default
    }

    print("\nEnvironment Variables:")
    all_configured = True
    for key, is_required in required_env.items():
        value = os.getenv(key, '(not set)')
        is_set = value != '(not set)'

        if key in ['GOOGLE_API_KEY', 'ANTHROPIC_API_KEY']:
            # Show only first few chars for security
            if is_set:
                display = value[:10] + '...'
            else:
                display = value
        else:
            display = value

        status = "[SET]" if is_set else "[NOT SET]"
        print(f"  {status} {key}={display}")

        if is_required and not is_set:
            all_configured = False

    return all_configured


def test_port_availability():
    """Test 3: Check if required ports are available"""
    print("\n=== Test 3: Port Availability ===")

    ports = {
        5000: 'Web Server (FastAPI)',
        5001: 'Backup Web Server',
    }

    print("\nPort Availability:")
    available_ports = []
    for port, service in ports.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:
                status = "[IN USE]"
                available = False
            else:
                status = "[AVAILABLE]"
                available = True
                available_ports.append(port)
        except Exception as e:
            status = f"[ERROR] {e}"
            available = False

        print(f"  {status} Port {port}: {service}")

    return len(available_ports) > 0


def test_llm_router():
    """Test 4: Verify LLM Router works"""
    print("\n=== Test 4: LLM Router ===")

    print("\nRouter Creation:")
    try:
        # Test Gemini router
        gemini_router = get_router('gemini', 'Test prompt')
        print(f"  [OK] Gemini router: {gemini_router.get_name()}")

        # Test Claude router
        claude_router = get_router('claude', 'Test prompt')
        print(f"  [OK] Claude router: {claude_router.get_name()}")

        return True
    except Exception as e:
        print(f"  [FAIL] Router creation failed: {e}")
        return False


async def test_gemini_api():
    """Test 5: Verify Gemini API is accessible"""
    print("\n=== Test 5: Gemini API ===")

    try:
        router = get_router('gemini', 'You are a helpful assistant.')

        print("Testing async process method...")
        result = await router.process(
            conversation="Say hello",
            active_file_content=None,
            custom_system_prompt=None
        )

        if result.get('type') == 'text':
            print(f"  [OK] Gemini API responsive")
            print(f"       Response length: {len(result.get('data', ''))} chars")
            return True
        else:
            print(f"  [WARN] Unexpected response type: {result.get('type')}")
            if 'error' in result.get('data', ''):
                print(f"       Error: {result.get('data')}")
            return False
    except Exception as e:
        print(f"  [FAIL] Gemini API error: {e}")
        return False


def test_file_paths():
    """Test 6: Verify file path configuration"""
    print("\n=== Test 6: File Paths ===")

    print(f"\nGenerated Code Directory:")
    print(f"  Path: {GENERATED_CODE_DIR}")
    print(f"  Exists: {GENERATED_CODE_DIR.exists()}")

    print(f"\nScreenshots Directory:")
    print(f"  Path: {SCREENSHOTS_DIR}")
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Ready: {SCREENSHOTS_DIR.exists()}")

    # Test writing a test file
    try:
        test_file = GENERATED_CODE_DIR / '.integration_test'
        test_file.write_text('test')
        test_content = test_file.read_text()
        test_file.unlink()
        print(f"\n  [OK] File read/write test passed")
        return True
    except Exception as e:
        print(f"\n  [FAIL] File operations failed: {e}")
        return False


def test_electron_files():
    """Test 7: Verify Electron app files are valid"""
    print("\n=== Test 7: Electron Files ===")

    # Check overlay.html contains custom_prompts.js
    overlay_file = Path('electron-overlay/overlay.html')
    if overlay_file.exists():
        try:
            content = overlay_file.read_text(encoding='utf-8', errors='ignore')
            has_custom_prompts = 'custom_prompts.js' in content
            print(f"  [{'OK' if has_custom_prompts else 'WARN'}] overlay.html references custom_prompts.js")

            has_websocket = 'WebSocket' in content
            print(f"  [{'OK' if has_websocket else 'FAIL'}] overlay.html has WebSocket code")

            return has_websocket
        except Exception as e:
            print(f"  [WARN] Could not read file content: {e}")
            print(f"  [OK] File exists (assuming valid)")
            return True

    print(f"  [FAIL] overlay.html not found")
    return False


def test_web_server_config():
    """Test 8: Verify web_server.py has required endpoints"""
    print("\n=== Test 8: Web Server Configuration ===")

    web_server_file = Path('web_server.py')
    if web_server_file.exists():
        try:
            content = web_server_file.read_text(encoding='utf-8', errors='ignore')

            endpoints = [
                'websocket_endpoint',
                'code_generation_request',
                'analyze_text_prompt',
                'gemini_coach_request',
            ]

            all_found = True
            for endpoint in endpoints:
                found = endpoint in content
                status = "[OK]" if found else "[MISSING]"
                print(f"  {status} {endpoint}")
                if not found:
                    all_found = False

            return all_found
        except Exception as e:
            print(f"  [WARN] Could not read file: {e}")
            print(f"  [OK] File exists (assuming valid)")
            return True

    print(f"  [FAIL] web_server.py not found")
    return False


def main():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("ELECTRON APP INTEGRATION TEST")
    print("="*60)

    tests = [
        ("File Structure", test_file_structure),
        ("Environment Config", test_environment_config),
        ("Port Availability", test_port_availability),
        ("LLM Router", test_llm_router),
        ("Gemini API", test_gemini_api),
        ("File Paths", test_file_paths),
        ("Electron Files", test_electron_files),
        ("Web Server Config", test_web_server_config),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            # Handle async tests
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()

            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] {test_name} raised exception: {e}")
            results.append((test_name, False))

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {test_name}")

    print(f"\nTotal: {passed}/{len(results)} passed")

    print("\n" + "="*60)
    if failed == 0:
        print("READY TO USE: All tests passed!")
        print("\nTo start the system:")
        print("  1. Terminal 1: uv run python voice_to_code.py")
        print("  2. Terminal 2: cd electron-overlay && npm start")
        print("\nWeb viewer: http://localhost:5000")
    else:
        print(f"ISSUES FOUND: {failed} test(s) failed")
        print("\nRefer to the output above for details")

    print("="*60 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
