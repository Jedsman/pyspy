"""
MCP Server for Voice-to-Code System
Exposes transcripts and screenshots as resources to Claude Desktop
"""

import asyncio
import json
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

# Initialize MCP server
server = Server("voice-to-code")

# Paths to transcript and screenshot files
LIVE_TRANSCRIPT_FILE = GENERATED_CODE_DIR / ".live_transcript"
TRANSCRIPT_FILE = GENERATED_CODE_DIR / ".transcript"


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
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
    """Handle tool execution requests"""

    if name == "capture_transcript":
        # Trigger transcript capture via command file
        command_file = GENERATED_CODE_DIR / ".command"
        command_file.write_text("capture_transcript")

        return [
            TextContent(
                type="text",
                text="Transcript capture triggered. The live buffer will be saved as a permanent segment.",
            )
        ]

    elif name == "capture_screenshot":
        # Trigger screenshot capture via command file
        command_file = GENERATED_CODE_DIR / ".command"
        command_file.write_text("capture_screenshot")

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

        # Add screenshot list
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
