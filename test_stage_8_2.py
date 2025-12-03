"""
Stage 8.2: MCP Server Testing
Tests the MCP server infrastructure and tools
"""

import json
import asyncio
from pathlib import Path
from config import GENERATED_CODE_DIR, SCREENSHOTS_DIR


def test_mcp_imports():
    """Test 8.2.1: MCP Module Imports"""
    print("\n=== Test 8.2.1: MCP Module Imports ===")
    
    try:
        from mcp.server import Server
        from mcp.types import Resource, Tool, TextContent, ImageContent
        from mcp.server.stdio import stdio_server
        print("[PASS] All MCP modules imported successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False


def test_mcp_server_creation():
    """Test 8.2.2: MCP Server Creation"""
    print("\n=== Test 8.2.2: MCP Server Creation ===")
    
    try:
        from mcp_server import server
        assert server.name == "voice-to-code", f"Expected 'voice-to-code', got {server.name}"
        print(f"[PASS] MCP Server created with name: {server.name}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_transcript_file_creation():
    """Test 8.2.3: Transcript File Structure"""
    print("\n=== Test 8.2.3: Transcript File Structure ===")
    
    try:
        # Create test transcript file
        transcript_file = GENERATED_CODE_DIR / ".live_transcript"
        test_data = {
            "buffer": [
                {"speaker": "User", "text": "Write hello world", "timestamp": "2025-12-03T10:00:00"},
                {"speaker": "System", "text": "Generating code...", "timestamp": "2025-12-03T10:00:01"}
            ],
            "timestamp": "2025-12-03T10:00:01"
        }
        
        transcript_file.write_text(json.dumps(test_data, indent=2))
        assert transcript_file.exists(), "Transcript file not created"
        print(f"[PASS] Transcript file created: {transcript_file}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_screenshot_creation():
    """Test 8.2.4: Screenshot File Handling"""
    print("\n=== Test 8.2.4: Screenshot File Handling ===")
    
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create a minimal test PNG (1x1 transparent pixel)
        test_png = bytes([
            137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82,
            0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0,
            0, 13, 73, 68, 65, 84, 8, 215, 99, 240, 207, 192, 0, 0, 3, 1, 1, 0,
            24, 108, 156, 89, 0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130
        ])
        
        screenshot_path = SCREENSHOTS_DIR / "test-capture-2025-12-03T10-00-00.png"
        screenshot_path.write_bytes(test_png)
        
        assert screenshot_path.exists(), "Screenshot file not created"
        print(f"[PASS] Test screenshot created: {screenshot_path}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_prompt_queue_creation():
    """Test 8.2.5: Prompt Queue File"""
    print("\n=== Test 8.2.5: Prompt Queue File ===")
    
    try:
        prompt_queue_file = GENERATED_CODE_DIR / ".prompt_queue.json"
        queue_data = [
            {
                "type": "adhoc",
                "prompt": "Explain this algorithm",
                "timestamp": "2025-12-03T10:00:00"
            }
        ]
        
        prompt_queue_file.write_text(json.dumps(queue_data, indent=2))
        assert prompt_queue_file.exists(), "Prompt queue file not created"
        print(f"[PASS] Prompt queue file created: {prompt_queue_file}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_claude_desktop_config():
    """Test 8.2.6: Claude Desktop Configuration"""
    print("\n=== Test 8.2.6: Claude Desktop Configuration ===")
    
    try:
        config_file = Path("claude_desktop_config.json")
        assert config_file.exists(), "claude_desktop_config.json not found"
        
        config = json.loads(config_file.read_text())
        assert "mcpServers" in config, "mcpServers section missing"
        assert "voice-to-code" in config["mcpServers"], "voice-to-code server config missing"
        
        server_config = config["mcpServers"]["voice-to-code"]
        assert server_config["command"] == "uv", "Command should be 'uv'"
        assert "mcp_server.py" in str(server_config["args"]), "mcp_server.py not in args"
        
        print(f"[PASS] Claude Desktop config is valid")
        print(f"  Command: {server_config['command']}")
        print(f"  Server: voice-to-code")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_claude_settings_permissions():
    """Test 8.2.7: Claude Settings Permissions"""
    print("\n=== Test 8.2.7: Claude Settings Permissions ===")
    
    try:
        settings_file = Path(".claude/settings.local.json")
        assert settings_file.exists(), ".claude/settings.local.json not found"
        
        settings = json.loads(settings_file.read_text())
        assert "permissions" in settings, "permissions section missing"
        
        perms = settings["permissions"]
        allow_list = perms.get("allow", [])
        
        required_perms = ["Bash(uv run:*)", "Bash(python -c:*)"]
        for perm in required_perms:
            assert perm in allow_list, f"Missing permission: {perm}"
        
        print(f"[PASS] Claude settings are valid")
        print(f"  Allow rules: {len(allow_list)}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def main():
    """Run all Stage 8.2 tests"""
    print("\n" + "="*60)
    print("STAGE 8.2: MCP SERVER TESTING")
    print("="*60)
    
    tests = [
        ("MCP Imports", test_mcp_imports),
        ("MCP Server Creation", test_mcp_server_creation),
        ("Transcript File", test_transcript_file_creation),
        ("Screenshot File", test_screenshot_creation),
        ("Prompt Queue", test_prompt_queue_creation),
        ("Claude Desktop Config", test_claude_desktop_config),
        ("Claude Settings", test_claude_settings_permissions),
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
    import sys
    success = main()
    sys.exit(0 if success else 1)
