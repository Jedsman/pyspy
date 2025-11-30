import asyncio
import base64
import subprocess
import tempfile
from io import BytesIO
from PIL import Image

# Import your MCP server
# This imports `server` and its route handlers
import mcp_server

from mcp.server.stdio import stdio_server
# gemini_mcp_client.py (Line 13)
from mcp import ClientSession # Use ClientSession from the top-level mcp package
from mcp.types import Resource
from mcp_server import NotificationOptions


#
# --- GEMINI CLI HELPERS ---
#

async def gemini_cli_text(prompt: str) -> str:
    """Call Gemini via CLI for text-only input."""
    result = subprocess.run(
        ["gemini", "generate-text", "--model", "gemini-2.0-pro", "--output", "text", prompt],
        capture_output=True,
        text=True
    )
    return result.stdout


async def gemini_cli_image(prompt: str, image_path: str) -> str:
    """Call Gemini via CLI with an image file."""
    result = subprocess.run(
        [
            "gemini",
            "generate-content",
            "--model", "gemini-2.0-pro-vision",
            "--input-file", image_path,
            "--output", "text",
            prompt
        ],
        capture_output=True,
        text=True
    )
    return result.stdout


#
# --- IMAGE LOADING (from MCP resource) ---
#

async def load_image_from_resource(client: ClientSession, uri: str) -> str:
    """Fetch base64 image, decode, save temp file, return file path."""
    data_url = await client.read_resource(uri)
    header, encoded = data_url.split(",", 1)
    raw = base64.b64decode(encoded)

    img = Image.open(BytesIO(raw))
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name)
    return temp.name


#
# --- MAIN GEMINI CLIENT ---
#

async def run_gemini_cli(client: ClientSession):
    """Interactive menu for Gemini-MCP client."""
    while True:
        print("\n=== Gemini MCP Client ===")
        print("1. List resources")
        print("2. Analyze screenshot (Gemini Vision)")
        print("3. Analyze transcript (Gemini Pro)")
        print("4. Exit")

        choice = input("> ")

        #
        # LIST RESOURCES
        #
        if choice == "1":
            resources = await client.list_resources()
            print("\nResources:")
            for r in resources:
                print(f"- {r.uri}: {r.name} ({r.mimeType})")

        #
        # ANALYZE SCREENSHOT
        #
        elif choice == "2":
            resources = await client.list_resources()
            screenshots = [r for r in resources if r.uri.startswith("screenshot:///")]

            if not screenshots:
                print("No screenshots available.")
                continue

            print("\nSelect screenshot:")
            for i, r in enumerate(screenshots):
                print(f"{i+1}: {r.name}")

            idx = int(input("> ")) - 1
            selected = screenshots[idx]

            image_path = await load_image_from_resource(client, selected.uri)
            prompt = input("\nWhat do you want Gemini to do with this image?\n> ")

            result = await gemini_cli_image(prompt, image_path)
            print("\n--- Gemini Output ---")
            print(result)

        #
        # ANALYZE TRANSCRIPT
        #
        elif choice == "3":
            resources = await client.list_resources()
            transcripts = [r for r in resources if r.uri.startswith("transcript://")]

            if not transcripts:
                print("No transcripts found.")
                continue

            print("\nSelect transcript:")
            for i, r in enumerate(transcripts):
                print(f"{i+1}: {r.name}")

            idx = int(input("> ")) - 1
            selected = transcripts[idx]

            text = await client.read_resource(selected.uri)
            prompt = input("\nAsk Gemini about the transcript:\n> ")

            combined = f"{prompt}\n\n{text}"
            result = await gemini_cli_text(combined)

            print("\n--- Gemini Output ---")
            print(result)

        #
        # EXIT
        #
        elif choice == "4":
            print("Goodbye.")
            break

        else:
            print("Invalid option.")


#
# --- EMBEDDING THE MCP SERVER ---
#

async def main():
    print("Starting embedded MCP server...")

    # start MCP server inside this same process
    async with stdio_server() as (read_stream, write_stream):
        server_task = asyncio.create_task(
            mcp_server.server.run(
                read_stream,
                write_stream,
                mcp_server.InitializationOptions(
                    server_name="embedded-mcp",
                    server_version="1.0.0",
                    capabilities=mcp_server.server.get_capabilities( # <--- CALL STARTS HERE
                        notification_options=mcp_server.NotificationOptions(), # <--- ADDED ARGUMENT 1
                        experimental_capabilities={},                         # <--- ADDED ARGUMENT 2
                    )                                                     # <--- CALL ENDS HERE
                )
            )
        )

        print("Connecting Gemini client to internal MCP server...")
        client = ClientSession(read_stream, write_stream)
        await client.initialize()

        await run_gemini_cli(client)

        server_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
