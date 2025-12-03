"""
Test WebSocket connection to web server
"""

import asyncio
import websockets
import json
import time
import subprocess
import sys
from pathlib import Path

async def test_websocket_connection():
    """Test that we can connect to the web server via WebSocket"""
    
    print("\n=== Testing WebSocket Connection ===\n")
    
    # Give server a moment to start
    await asyncio.sleep(1)
    
    try:
        async with websockets.connect("ws://localhost:5000/ws") as websocket:
            print("Connected to WebSocket server on localhost:5000/ws")
            
            # Send a test message
            test_message = {
                "type": "test_message",
                "data": "Hello from test"
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"Sent test message: {test_message}")
            
            # Try to receive response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2)
                print(f"Received response: {response[:100]}...")
                return True
            except asyncio.TimeoutError:
                print("No response received (normal - server may not echo test messages)")
                return True
                
    except Exception as e:
        print(f"WebSocket connection failed: {e}")
        return False

async def main():
    print("Testing WebSocket connection to web server")
    print("="*50)
    
    # Start web server
    print("\nStarting web server...")
    server_process = subprocess.Popen(
        ["uv", "run", "python", "web_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Test connection
        result = await test_websocket_connection()
        
        if result:
            print("\nWebSocket test: PASS")
            print("\nElectron app can now connect to the web server!")
            print("Start web_server.py and Electron app separately:")
            print("  Terminal 1: uv run python voice_to_code.py")
            print("  Terminal 2: cd electron-overlay && npm start")
            return 0
        else:
            print("\nWebSocket test: FAIL")
            return 1
    finally:
        # Kill server
        server_process.terminate()
        server_process.wait(timeout=5)

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
