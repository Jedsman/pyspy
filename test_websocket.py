import asyncio
import websockets
import json

async def test_analyze_screenshot():
    """
    Connects to the WebSocket server and sends a test message
    for the 'analyze_screenshot' functionality.
    """
    uri = "ws://localhost:5000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")

            # The test message payload
            test_payload = {
              "type": "analyze_screenshot",
              "prompt": "Explain this code snippet.",
              "screenshot_path": "C:\\path\\to\\dummy\\screenshot.png"
            }

            # Send the JSON message to the server
            await websocket.send(json.dumps(test_payload))
            print(f"\n>>> Sent message to server:\n{json.dumps(test_payload, indent=2)}")

            print("\n---")
            print("Check the web_server.py console output to verify the message was received.")
            print("The script will exit in a few seconds.")
            await asyncio.sleep(3) # Keep connection open briefly

    except ConnectionRefusedError:
        print(f"Connection to {uri} refused. Is the web_server.py running?")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Ensure the web_server.py is running in another terminal
    # before executing this script.
    asyncio.run(test_analyze_screenshot())
