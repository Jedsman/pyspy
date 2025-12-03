"""
Verify web server can start without errors
"""

import sys
import time
import subprocess
import socket

def check_port_listening(port=5000, timeout=5):
    """Check if port is listening"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

print("\n=== Verifying Web Server Can Start ===\n")

# Start web server
print("Starting web server on localhost:5000...")
server = subprocess.Popen(
    ["uv", "run", "python", "web_server.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

try:
    # Wait for server to start
    print("Waiting for server to bind to port 5000...")
    if check_port_listening(port=5000, timeout=5):
        print("SUCCESS: Web server is listening on port 5000")
        print("\nElectron app WebSocket connection is now possible!")
        print("\nTo use the system:")
        print("  1. Terminal 1: uv run python voice_to_code.py")
        print("  2. Terminal 2: cd electron-overlay && npm start")
        print("  3. Browser: http://localhost:5000")
        exit_code = 0
    else:
        print("FAILED: Web server did not bind to port 5000")
        # Print any errors
        stdout, stderr = server.communicate(timeout=2)
        if stderr:
            print(f"\nServer errors:\n{stderr}")
        exit_code = 1
except Exception as e:
    print(f"ERROR: {e}")
    exit_code = 1
finally:
    try:
        server.terminate()
        server.wait(timeout=2)
    except:
        server.kill()

print("\n" + "="*50)
sys.exit(exit_code)
