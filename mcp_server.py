"""
MCP Server for Voice-to-Code System
Exposes transcripts and screenshots as resources to Claude Desktop
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
import base64

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Import centralized config
from config import GENERATED_CODE_DIR, SCREENSHOTS_DIR

# Set up logging for MCP server debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='[MCP] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(GENERATED_CODE_DIR / 'mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("voice-to-code")

# Paths to transcript and screenshot files
LIVE_TRANSCRIPT_FILE = GENERATED_CODE_DIR / ".live_transcript"
TRANSCRIPT_FILE = GENERATED_CODE_DIR / ".transcript"
PROMPT_QUEUE_FILE = GENERATED_CODE_DIR / ".prompt_queue.json"
CODE_GENERATION_QUEUE_FILE = GENERATED_CODE_DIR / ".code_generation_queue.json"
COMMAND_FILE = GENERATED_CODE_DIR / ".command"


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available transcript and screenshot resources"""
    resources = []

    # Live transcript buffer resource
    if LIVE_TRANSCRIPT_FILE.exists():
        resources.append(
            Resource(
                uri=f"transcript://live",
                name="Live Transcript Buffer",
                description="Real-time transcript of ongoing conversation",
                mimeType="application/json",
            )
        )

    # Captured transcript segments
    resources.append(
        Resource(
            uri=f"transcript://segments",
            name="Captured Transcript Segments",
            description="All manually captured transcript segments",
            mimeType="application/json",
        )
    )

    # Screenshot resources
    if SCREENSHOTS_DIR.exists():
        for screenshot in sorted(SCREENSHOTS_DIR.glob("*.png"), reverse=True):
            resources.append(
                Resource(
                    uri=f"screenshot:///{screenshot.name}",
                    name=f"Screenshot: {screenshot.stem}",
                    description=f"Screenshot captured at {screenshot.stem}",
                    mimeType="image/png",
                )
            )

    return resources


@server.read_resource()
async def handle_read_resource(uri: str) -> str | list[TextContent | ImageContent]:
    """Read transcript or screenshot resource content"""

    if uri.startswith("transcript://live"):
        # Return live transcript buffer
        if LIVE_TRANSCRIPT_FILE.exists():
            with open(LIVE_TRANSCRIPT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Format as readable text
            buffer = data.get('buffer', [])
            if not buffer:
                return "No active transcript in buffer."

            formatted = []
            formatted.append("=== LIVE TRANSCRIPT BUFFER ===\n")
            for item in buffer:
                speaker = item.get('speaker', 'Unknown')
                text = item.get('text', '')
                timestamp = item.get('timestamp', '')
                formatted.append(f"[{speaker}] {text}")

            formatted.append(f"\nLast updated: {data.get('timestamp', 'Unknown')}")
            return "\n".join(formatted)
        else:
            return "No live transcript available."

    elif uri.startswith("transcript://segments"):
        # Return all captured segments from history
        segments_file = GENERATED_CODE_DIR / ".transcript_history"
        if segments_file.exists():
            with open(segments_file, 'r', encoding='utf-8') as f:
                segments = json.load(f)

            if not segments:
                return "No captured transcript segments."

            formatted = []
            formatted.append("=== CAPTURED TRANSCRIPT SEGMENTS ===\n")
            for i, segment in enumerate(segments, 1):
                speaker = segment.get('speaker', 'Unknown')
                text = segment.get('text', '')
                timestamp = segment.get('timestamp', '')
                formatted.append(f"Segment {i} [{speaker}] ({timestamp}):")
                formatted.append(f"{text}\n")

            return "\n".join(formatted)
        else:
            return "No captured segments available."

    elif uri.startswith("screenshot:///"):
        # Return screenshot as ImageContent
        screenshot_name = uri.replace("screenshot:///", "")
        screenshot_path = SCREENSHOTS_DIR / screenshot_name

        if screenshot_path.exists():
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Return as a list containing ImageContent
            return [
                ImageContent(
                    type="image",
                    data=image_data,
                    mimeType="image/png"
                )
            ]
        else:
            raise ValueError(f"Screenshot not found: {screenshot_name}")

    else:
        raise ValueError(f"Unknown resource URI: {uri}")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools for interacting with the system"""
    return [
        Tool(
            name="capture_transcript",
            description="Capture the current live transcript buffer as a permanent segment",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="capture_screenshot",
            description="Capture a screenshot of the current screen",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_interview_context",
            description="Get full interview context including all transcripts and recent screenshots",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="view_screenshot",
            description="View a specific screenshot by filename",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The screenshot filename (e.g., 'capture-2025-12-01T22-31-45-123Z.png')",
                    }
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="check_prompt_queue",
            description="Check for pending screenshot analysis requests. Returns any queued prompts with their associated screenshots. Call this periodically or when notified of new captures.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="check_code_generation_queue",
            description="Check for pending code generation requests (new_code or update_code). Returns the prompt, transcripts, and action type. Call this to get code generation tasks from the overlay.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
    """Handle tool execution requests"""
    logger.info(f"Tool called: {name}")

    if name == "capture_transcript":
        # Trigger transcript capture via command file
        logger.info("Writing capture_transcript to command file")
        COMMAND_FILE.write_text("capture_transcript")
        logger.info("Transcript capture triggered")

        return [
            TextContent(
                type="text",
                text="Transcript capture triggered. The live buffer will be saved as a permanent segment.",
            )
        ]

    elif name == "capture_screenshot":
        # Trigger screenshot capture via command file
        logger.info("Writing capture_screenshot to command file")
        COMMAND_FILE.write_text("capture_screenshot")
        logger.info("Screenshot capture triggered")

        return [
            TextContent(
                type="text",
                text="Screenshot capture triggered. The screenshot will be saved to the screenshots directory.",
            )
        ]

    elif name == "get_interview_context":
        # Get comprehensive interview context
        context_parts = []

        # Add live transcript
        if LIVE_TRANSCRIPT_FILE.exists():
            with open(LIVE_TRANSCRIPT_FILE, 'r', encoding='utf-8') as f:
                live_data = json.load(f)
            buffer = live_data.get('buffer', [])
            if buffer:
                context_parts.append("=== LIVE TRANSCRIPT ===")
                for item in buffer:
                    speaker = item.get('speaker', 'Unknown')
                    text = item.get('text', '')
                    context_parts.append(f"[{speaker}] {text}")
                context_parts.append("")

        # Add captured segments
        segments_file = GENERATED_CODE_DIR / ".transcript_history"
        if segments_file.exists():
            with open(segments_file, 'r', encoding='utf-8') as f:
                segments = json.load(f)
            if segments:
                context_parts.append("=== CAPTURED SEGMENTS ===")
                for i, segment in enumerate(segments[-10:], 1):  # Last 10 segments
                    speaker = segment.get('speaker', 'Unknown')
                    text = segment.get('text', '')
                    context_parts.append(f"[{speaker}] {text}")
                context_parts.append("")

        # Add screenshots
        if SCREENSHOTS_DIR.exists():
            screenshots = sorted(SCREENSHOTS_DIR.glob("*.png"), reverse=True)
            if screenshots:
                context_parts.append(f"=== SCREENSHOTS ===")
                context_parts.append(f"{len(screenshots)} screenshot(s) available:")
                context_parts.append("To view a screenshot, use the view_screenshot tool with the filename.")
                for screenshot in screenshots[:5]:  # Show last 5 screenshots
                    context_parts.append(f"  - {screenshot.name}")
                if len(screenshots) > 5:
                    context_parts.append(f"  ... and {len(screenshots) - 5} more")

        return [
            TextContent(
                type="text",
                text="\n".join(context_parts) if context_parts else "No interview context available yet.",
            )
        ]

    elif name == "view_screenshot":
        # View a specific screenshot by filename
        filename = arguments.get("filename")
        if not filename:
            return [
                TextContent(
                    type="text",
                    text="Error: No filename provided.",
                )
            ]

        screenshot_path = SCREENSHOTS_DIR / filename
        if screenshot_path.exists():
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            return [
                ImageContent(
                    type="image",
                    data=image_data,
                    mimeType="image/png"
                )
            ]
        else:
            return [
                TextContent(
                    type="text",
                    text=f"Screenshot not found: {filename}",
                )
            ]

    elif name == "check_prompt_queue":
        # Check for queued screenshot analysis requests and adhoc prompts
        logger.info(f"check_prompt_queue called - queue file path: {PROMPT_QUEUE_FILE}")

        if not PROMPT_QUEUE_FILE.exists():
            logger.info("Queue file does not exist - no pending requests")
            return [
                TextContent(
                    type="text",
                    text="No pending requests.",
                )
            ]

        logger.info(f"Queue file exists, reading from {PROMPT_QUEUE_FILE}")

        try:
            with open(PROMPT_QUEUE_FILE, 'r', encoding='utf-8') as f:
                queue_content = f.read()
                logger.debug(f"Raw queue file content: {queue_content}")
                queue = json.loads(queue_content)

            logger.info(f"Queue loaded successfully - {len(queue)} item(s) in queue")

            if not queue or len(queue) == 0:
                # Empty queue, delete file
                logger.info("Queue is empty, deleting queue file")
                PROMPT_QUEUE_FILE.unlink()
                return [
                    TextContent(
                        type="text",
                        text="No pending requests.",
                    )
                ]

            # Get the first item from queue
            item = queue.pop(0)
            prompt_text = item.get('prompt', '')
            timestamp = item.get('timestamp', '')
            item_type = item.get('type', 'screenshot')  # 'adhoc' or 'screenshot'
            filename = item.get('filename', '')

            logger.info(f"Processing queue item: type={item_type}, filename={filename}, timestamp={timestamp}")
            logger.debug(f"Prompt text: {prompt_text[:100]}..." if len(prompt_text) > 100 else f"Prompt text: {prompt_text}")

            # Update queue file (remove processed item)
            if len(queue) == 0:
                logger.info("Queue is now empty after processing, deleting queue file")
                PROMPT_QUEUE_FILE.unlink()
            else:
                logger.info(f"Queue now has {len(queue)} remaining item(s), updating queue file")
                with open(PROMPT_QUEUE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(queue, f, indent=2)

            # Handle adhoc prompts (no screenshot)
            if item_type == 'adhoc':
                logger.info("Returning adhoc text prompt to Claude Desktop")
                return [
                    TextContent(
                        type="text",
                        text=f"Prompt from overlay:\n\n{prompt_text}",
                    )
                ]

            # Handle screenshot analysis requests (with screenshot)
            logger.info(f"Looking for screenshot file: {filename}")
            screenshot_path = SCREENSHOTS_DIR / filename

            if not screenshot_path.exists():
                logger.error(f"Screenshot file not found: {screenshot_path}")
                return [
                    TextContent(
                        type="text",
                        text=f"Screenshot file not found: {filename}",
                    )
                ]

            logger.info(f"Screenshot file found, reading: {screenshot_path}")
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            logger.info(f"Screenshot encoded successfully ({len(image_data)} bytes), returning to Claude Desktop")

            # Return the prompt text and the screenshot
            return [
                TextContent(
                    type="text",
                    text=f"Screenshot analysis request:\n\n{prompt_text}\n\nScreenshot: {filename}\nCaptured at: {timestamp}",
                ),
                ImageContent(
                    type="image",
                    data=image_data,
                    mimeType="image/png"
                )
            ]

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse queue file as JSON: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: Invalid queue file format (JSON parse error): {str(e)}",
                )
            ]
        except Exception as e:
            logger.error(f"Error reading prompt queue: {str(e)}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=f"Error reading prompt queue: {str(e)}",
                )
            ]

    elif name == "check_code_generation_queue":
        # Check for queued code generation requests
        logger.info(f"check_code_generation_queue called - queue file path: {CODE_GENERATION_QUEUE_FILE}")

        if not CODE_GENERATION_QUEUE_FILE.exists():
            logger.info("Code generation queue file does not exist - no pending requests")
            return [
                TextContent(
                    type="text",
                    text="No pending code generation requests.",
                )
            ]

        logger.info(f"Code generation queue file exists, reading from {CODE_GENERATION_QUEUE_FILE}")

        try:
            with open(CODE_GENERATION_QUEUE_FILE, 'r', encoding='utf-8') as f:
                queue_content = f.read()
                logger.debug(f"Raw code generation queue content: {queue_content}")
                queue = json.loads(queue_content)

            logger.info(f"Code generation queue loaded successfully - {len(queue)} item(s) in queue")

            if not queue or len(queue) == 0:
                logger.info("Code generation queue is empty, deleting queue file")
                CODE_GENERATION_QUEUE_FILE.unlink()
                return [
                    TextContent(
                        type="text",
                        text="No pending code generation requests.",
                    )
                ]

            # Get the first item from queue
            item = queue.pop(0)
            action = item.get('action', 'new_code')
            prompt_text = item.get('prompt', '')
            transcripts = item.get('transcripts', '')
            timestamp = item.get('timestamp', '')

            logger.info(f"Processing code generation request: action={action}, timestamp={timestamp}")
            logger.debug(f"Prompt: {prompt_text[:100]}...")
            logger.debug(f"Transcripts: {transcripts[:200]}...")

            # Update queue file (remove processed item)
            if len(queue) == 0:
                logger.info("Code generation queue is now empty after processing, deleting queue file")
                CODE_GENERATION_QUEUE_FILE.unlink()
            else:
                logger.info(f"Code generation queue now has {len(queue)} remaining item(s), updating queue file")
                with open(CODE_GENERATION_QUEUE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(queue, f, indent=2)

            # Return the code generation request details
            return [
                TextContent(
                    type="text",
                    text=f"Code Generation Request ({action}):\n\nPrompt:\n{prompt_text}\n\nSelected Transcripts:\n{transcripts}\n\nRequested at: {timestamp}",
                )
            ]

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse code generation queue file as JSON: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: Invalid code generation queue file format (JSON parse error): {str(e)}",
                )
            ]
        except Exception as e:
            logger.error(f"Error reading code generation queue: {str(e)}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=f"Error reading code generation queue: {str(e)}",
                )
            ]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="voice-to-code",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
