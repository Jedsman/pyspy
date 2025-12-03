"""
Web Server for Real-Time Code Viewer
Displays generated code files in a web interface with live updates via WebSocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uvicorn
from typing import Set
import os
import time

app = FastAPI()

# Track connected WebSocket clients
connected_clients: Set[WebSocket] = set()

# Path to generated code folder
GENERATED_CODE_DIR = Path("generated_code")
SCREENSHOTS_DIR = GENERATED_CODE_DIR / "screenshots"

# Path to command file for IPC
COMMAND_FILE = Path("generated_code") / ".command"

# Path to coach suggestions file for IPC
COACH_SUGGESTIONS_FILE = Path("generated_code") / ".coach_suggestions"

# Path to current mode file for IPC
CURRENT_MODE_FILE = Path("generated_code") / ".current_mode"

# Path to transcript file for IPC
TRANSCRIPT_FILE = Path("generated_code") / ".transcript"

# Path to live transcript buffer for IPC
LIVE_TRANSCRIPT_FILE = Path("generated_code") / ".live_transcript"


class CodeFileHandler(FileSystemEventHandler):
    """Watches for file changes in the generated_code directory"""

    def __init__(self, broadcast_func):
        self.broadcast_func = broadcast_func
        self.session_files = set()  # Track files created in this session
        self.last_broadcast = {}  # Track last broadcast time per file to prevent duplicates
        self.debounce_delay = 0.1  # 100ms debounce delay

    def should_broadcast(self, filepath: Path) -> bool:
        """Check if enough time has passed since last broadcast for this file"""
        file_key = str(filepath)
        current_time = time.time()

        if file_key not in self.last_broadcast:
            self.last_broadcast[file_key] = current_time
            return True

        time_since_last = current_time - self.last_broadcast[file_key]
        if time_since_last >= self.debounce_delay:
            self.last_broadcast[file_key] = current_time
            return True

        return False

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        self.session_files.add(filepath.name)
        asyncio.run(self.broadcast_file_update(filepath, "created"))

    def on_modified(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        print(f"DEBUG: File modified detected by watchdog: {filepath.name}") # Added general debug log

        # Use debouncing to prevent duplicate broadcasts
        if not self.should_broadcast(filepath):
            return

        # Check if it's a coach suggestions update
        if filepath.name == ".coach_suggestions":
            print(f"DEBUG: Handling coach suggestions for {filepath.name}") # Added specific debug log
            asyncio.run(self.broadcast_coach_suggestions(filepath))
            return

        # Check if it's a mode change update
        if filepath.name == ".current_mode":
            print(f"DEBUG: Handling mode change for {filepath.name}") # Added specific debug log
            asyncio.run(self.broadcast_mode_change(filepath))
            return

        # Check if it's a transcript update
        if filepath.name == ".transcript":
            print(f"DEBUG: Handling transcript update for {filepath.name}") # Added specific debug log
            asyncio.run(self.broadcast_transcript(filepath))
            return

        # Check if it's a live transcript buffer update
        if filepath.name == ".live_transcript":
            print(f"DEBUG: Handling live transcript buffer for {filepath.name}") # Added specific debug log
            asyncio.run(self.broadcast_live_transcript(filepath))
            return

        # Check if it's a screenshot saved notification
        if filepath.name == ".screenshot_saved":
            print(f"DEBUG: Handling screenshot saved for {filepath.name}") # Added specific debug log
            asyncio.run(self.broadcast_screenshot_saved(filepath))
            return

        # Only broadcast if this file was created in this session
        if filepath.name in self.session_files:
            asyncio.run(self.broadcast_file_update(filepath, "modified"))

    async def broadcast_coach_suggestions(self, filepath: Path):
        """Read coach suggestions and broadcast to all connected clients"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            message = {
                'type': 'coach_suggestion',
                'question': data.get('question', ''),
                'suggestions': data.get('suggestions', []),
                'timestamp': data.get('timestamp', '')
            }

            await self.broadcast_func(message)

        except Exception as e:
            print(f"Error broadcasting coach suggestions: {e}")

    async def broadcast_mode_change(self, filepath: Path):
        """Read mode change and broadcast to all connected clients"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            message = {
                'type': 'mode_change',
                'mode': data.get('mode', 'Code'),
                'timestamp': data.get('timestamp', '')
            }
            print(f"DEBUG: Broadcasting mode change message: {message}") # Added debug log before broadcast

            await self.broadcast_func(message)

        except Exception as e:
            print(f"Error broadcasting mode change: {e}")

    async def broadcast_transcript(self, filepath: Path):
        """Read transcript segment and broadcast to all connected clients"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            message = {
                'type': 'transcript',
                'speaker': data.get('speaker', 'Unknown'),
                'text': data.get('text', ''),
                'timestamp': data.get('timestamp', '')
            }

            await self.broadcast_func(message)

        except Exception as e:
            print(f"Error broadcasting transcript: {e}")

    async def broadcast_live_transcript(self, filepath: Path):
        """Read live transcript buffer and broadcast to all connected clients"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            message = {
                'type': 'live_transcript',
                'buffer': data.get('buffer', []),
                'timestamp': data.get('timestamp', '')
            }

            await self.broadcast_func(message)

        except Exception as e:
            print(f"Error broadcasting live transcript: {e}")

    async def broadcast_screenshot_saved(self, filepath: Path):
        """Read the path of the saved screenshot and broadcast it."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            message = {
                'type': 'screenshot_saved',
                'path': data.get('path', ''),
                'timestamp': data.get('timestamp', '')
            }

            await self.broadcast_func(message)

        except Exception as e:
            print(f"Error broadcasting screenshot saved notification: {e}")

    async def broadcast_file_update(self, filepath: Path, action: str):
        """Read file content and broadcast to all connected clients"""
        # Skip control files (dot files)
        if filepath.name.startswith('.'):
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Detect language from file extension
            ext = filepath.suffix.lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.html': 'html',
                '.css': 'css',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.go': 'go',
                '.rs': 'rust',
                '.rb': 'ruby',
                '.php': 'php',
                '.sql': 'sql',
                '.sh': 'bash',
                '.json': 'json',
                '.xml': 'xml',
                '.md': 'markdown',
            }
            language = language_map.get(ext, 'python')

            message = {
                'action': action,
                'filename': filepath.name,
                'content': content,
                'language': language
            }

            await self.broadcast_func(message)

        except Exception as e:
            print(f"Error broadcasting file update: {e}")


async def broadcast_to_clients(message: dict):
    """Send message to all connected WebSocket clients"""
    if not connected_clients:
        return

    # Remove disconnected clients
    dead_clients = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            dead_clients.add(client)

    # Clean up dead connections
    for client in dead_clients:
        connected_clients.discard(client)


@app.get("/", response_class=HTMLResponse)
async def get_viewer():
    """Serve the code viewer HTML page"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice-to-Code Viewer</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Semi-transparent overlay mode */
        body.overlay-mode {
            background: rgba(30, 30, 30, 0.85);
        }

        body.overlay-mode .tab-container,
        body.overlay-mode .code-container {
            background: rgba(30, 30, 30, 0.9);
        }

        .header {
            background: #252526;
            padding: 10px 20px;
            border-bottom: 1px solid #3e3e42;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 18px;
            color: #cccccc;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4caf50;
            animation: pulse 2s infinite;
        }

        .status-indicator.disconnected {
            background: #f44336;
            animation: none;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .controls {
            display: flex;
            gap: 10px;
        }

        .btn {
            padding: 5px 15px;
            background: #0e639c;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 13px;
        }

        .btn-generate {
            background: #4caf50;
        }

        .btn-generate:hover {
            background: #45a049;
        }

        .btn-update {
            background: #ff9800;
        }

        .btn-update:hover {
            background: #e68900;
        }

        .btn:hover {
            background: #1177bb;
        }

        .tab-container {
            background: #252526;
            display: flex;
            overflow-x: auto;
            border-bottom: 1px solid #3e3e42;
            max-height: 40px;
        }

        .tab-container::-webkit-scrollbar {
            height: 6px;
        }

        .tab-container::-webkit-scrollbar-thumb {
            background: #424242;
            border-radius: 3px;
        }

        .tab {
            padding: 10px 20px;
            background: #2d2d30;
            border-right: 1px solid #3e3e42;
            cursor: pointer;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 10px;
            position: relative;
        }

        .tab:hover {
            background: #37373d;
        }

        .tab.active {
            background: #1e1e1e;
            color: #ffffff;
        }

        .tab.updating {
            animation: flash 0.5s;
        }

        @keyframes flash {
            0%, 100% { background: #2d2d30; }
            50% { background: #4caf50; }
        }

        .tab-close {
            color: #858585;
            font-size: 16px;
            line-height: 1;
            cursor: pointer;
            padding: 0 5px;
        }

        .tab-close:hover {
            color: #ffffff;
        }

        .code-container {
            flex: 1;
            overflow: auto;
            background: #1e1e1e;
            position: relative;
        }

        .code-panel {
            display: none;
            height: 100%;
        }

        .code-panel.active {
            display: block;
        }

        .updating-indicator {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #4caf50;
            color: white;
            padding: 5px 15px;
            border-radius: 3px;
            font-size: 12px;
            display: none;
            z-index: 1000;
        }

        .updating-indicator.show {
            display: block;
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        pre {
            margin: 0 !important;
            height: 100%;
        }

        pre code {
            height: 100%;
            display: block;
        }

        .line-numbers {
            padding: 20px 10px !important;
        }

        .no-files {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #858585;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ Voice-to-Code Viewer</h1>
        <div class="status">
            <div class="status-indicator" id="status"></div>
            <span id="status-text">Connected</span>
            <div class="controls">
                <button class="btn btn-generate" onclick="sendGenerate()">🆕 New File</button>
                <button class="btn btn-update" onclick="sendUpdate()">💾 Update File</button>
                <button class="btn" onclick="toggleOverlay()">Toggle Overlay (F9)</button>
            </div>
        </div>
    </div>

    <div class="tab-container" id="tabs"></div>

    <div class="code-container">
        <div class="updating-indicator" id="updating">Updating...</div>
        <div id="code-panels">
            <div class="no-files">Waiting for generated files...</div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-typescript.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-java.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-cpp.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-go.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-rust.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.css">

    <script>
        const tabs = {};
        let activeTab = null;
        let ws = null;

        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('status').classList.remove('disconnected');
                document.getElementById('status-text').textContent = 'Connected';
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                document.getElementById('status').classList.add('disconnected');
                document.getElementById('status-text').textContent = 'Disconnected';
                setTimeout(connect, 3000);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleFileUpdate(data);
            };
        }

        function handleFileUpdate(data) {
            const { action, filename, content, language } = data;

            // Show updating indicator
            const indicator = document.getElementById('updating');
            indicator.classList.add('show');
            setTimeout(() => indicator.classList.remove('show'), 1500);

            if (action === 'created' || action === 'modified') {
                if (!tabs[filename]) {
                    createTab(filename, content, language);
                } else {
                    updateTab(filename, content, language);
                }
            }
        }

        function createTab(filename, content, language) {
            // Create tab
            const tabContainer = document.getElementById('tabs');
            const tab = document.createElement('div');
            tab.className = 'tab';
            tab.innerHTML = `
                <span>${filename}</span>
                <span class="tab-close" onclick="closeTab('${filename}', event)">×</span>
            `;
            tab.onclick = (e) => {
                if (!e.target.classList.contains('tab-close')) {
                    switchTab(filename);
                }
            };
            tabContainer.appendChild(tab);

            // Create code panel
            const codePanels = document.getElementById('code-panels');
            const panel = document.createElement('div');
            panel.className = 'code-panel';
            panel.id = `panel-${filename}`;

            const pre = document.createElement('pre');
            pre.className = 'line-numbers';
            const code = document.createElement('code');
            code.className = `language-${language}`;
            code.textContent = content;
            pre.appendChild(code);
            panel.appendChild(pre);

            codePanels.appendChild(panel);

            // Store tab data
            tabs[filename] = {
                tab: tab,
                panel: panel,
                language: language
            };

            // Hide "no files" message
            const noFiles = document.querySelector('.no-files');
            if (noFiles) noFiles.remove();

            // Activate this tab
            switchTab(filename);

            // Apply syntax highlighting
            Prism.highlightElement(code);
        }

        function updateTab(filename, content, language) {
            const tabData = tabs[filename];
            if (!tabData) return;

            // Flash the tab
            tabData.tab.classList.add('updating');
            setTimeout(() => tabData.tab.classList.remove('updating'), 500);

            // Store scroll position
            const panel = tabData.panel;
            const scrollTop = panel.scrollTop;

            // Update content
            const code = panel.querySelector('code');
            code.textContent = content;
            code.className = `language-${language}`;

            // Reapply syntax highlighting
            Prism.highlightElement(code);

            // Restore scroll position
            panel.scrollTop = scrollTop;
        }

        function switchTab(filename) {
            // Deactivate all tabs
            Object.values(tabs).forEach(t => {
                t.tab.classList.remove('active');
                t.panel.classList.remove('active');
            });

            // Activate selected tab
            if (tabs[filename]) {
                tabs[filename].tab.classList.add('active');
                tabs[filename].panel.classList.add('active');
                activeTab = filename;
            }
        }

        function closeTab(filename, event) {
            event.stopPropagation();

            const tabData = tabs[filename];
            if (!tabData) return;

            // Remove DOM elements
            tabData.tab.remove();
            tabData.panel.remove();

            // Remove from tabs object
            delete tabs[filename];

            // If this was the active tab, switch to another
            if (activeTab === filename) {
                const remainingTabs = Object.keys(tabs);
                if (remainingTabs.length > 0) {
                    switchTab(remainingTabs[0]);
                } else {
                    // No tabs left, show "no files" message
                    const codePanels = document.getElementById('code-panels');
                    codePanels.innerHTML = '<div class="no-files">Waiting for generated files...</div>';
                    activeTab = null;
                }
            }
        }

        async function sendGenerate() {
            try {
                const response = await fetch('/api/command/generate', {
                    method: 'POST'
                });
                const result = await response.json();
                if (result.status === 'success') {
                    console.log('Generate command sent successfully');
                }
            } catch (error) {
                console.error('Error sending generate command:', error);
            }
        }

        async function sendUpdate() {
            try {
                const response = await fetch('/api/command/update', {
                    method: 'POST'
                });
                const result = await response.json();
                if (result.status === 'success') {
                    console.log('Update command sent successfully');
                }
            } catch (error) {
                console.error('Error sending update command:', error);
            }
        }

        function toggleOverlay() {
            document.body.classList.toggle('overlay-mode');
        }

        // F9 key to toggle overlay mode
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F9') {
                e.preventDefault();
                toggleOverlay();
            }
        });

        // Connect on load
        connect();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/command/generate")
async def trigger_generate():
    """Trigger code generation (new file)"""
    try:
        COMMAND_FILE.write_text("generate")
        return {"status": "success", "command": "generate"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/command/update")
async def trigger_update():
    """Trigger code update (modify active file)"""
    try:
        COMMAND_FILE.write_text("update")
        return {"status": "success", "command": "update"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/mode/toggle")
async def toggle_mode():
    """Toggle between Code Generation and Interview Coach mode"""
    try:
        COMMAND_FILE.write_text("toggle_mode")
        return {"status": "success", "command": "toggle_mode"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/transcript/capture")
async def capture_transcript():
    """Capture current live transcript buffer as a segment"""
    try:
        COMMAND_FILE.write_text("capture_transcript")
        return {"status": "success", "command": "capture_transcript"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/command/transcript_window")
async def transcript_window_command(request: dict):
    """Handle transcript window open/close commands"""
    try:
        command = request.get('command', '')
        if command in ['transcript_window_opened', 'transcript_window_closed']:
            COMMAND_FILE.write_text(command)
            return {"status": "success", "command": command}
        else:
            return {"status": "error", "message": "Invalid command"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/screenshot/area")
async def capture_screenshot_area(request: dict):
    """Capture a selected area of the screen"""
    try:
        x = request.get('x', 0)
        y = request.get('y', 0)
        width = request.get('width', 0)
        height = request.get('height', 0)

        # Write screenshot command with coordinates
        command_data = {
            "command": "capture_screenshot_area",
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        COMMAND_FILE.write_text(json.dumps(command_data))

        # Generate filename for response
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

        return {"status": "success", "command": "capture_screenshot_area", "filename": filename}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        # Send existing files to newly connected client (if enabled)
        load_existing = os.getenv("LOAD_EXISTING_FILES", "true").lower() == "true"

        if load_existing and GENERATED_CODE_DIR.exists():
            for filepath in sorted(GENERATED_CODE_DIR.glob("*"), key=lambda p: p.stat().st_mtime):
                # Skip control files (dot files)
                if filepath.is_file() and not filepath.name.startswith('.'):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        ext = filepath.suffix.lower()
                        language_map = {
                            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                            '.html': 'html', '.css': 'css', '.java': 'java',
                            '.cpp': 'cpp', '.c': 'c', '.go': 'go', '.rs': 'rust',
                        }
                        language = language_map.get(ext, 'python')

                        await websocket.send_json({
                            'action': 'created',
                            'filename': filepath.name,
                            'content': content,
                            'language': language
                        })
                    except:
                        pass

        # Keep connection alive
        while True:
            # Wait for a message from the client
            message_text = await websocket.receive_text()
            try:
                data = json.loads(message_text)
                message_type = data.get('type')

                # Handle screenshot analysis requests
                if message_type == 'analyze_screenshot':
                    prompt = data.get('prompt', 'No prompt provided')
                    file_name = data.get('fileName') # Expecting fileName now, not screenshot_path

                    if not file_name:
                        print("⚠️  'analyze_screenshot' message received without a 'fileName'.")
                        continue

                    # Construct the full, local path on the server
                    full_screenshot_path = SCREENSHOTS_DIR / file_name

                    # Forward the command to voice_to_code.py via the .command file
                    command_data = {"command": "analyze_screenshot", "prompt": prompt, "screenshot_path": str(full_screenshot_path)}
                    COMMAND_FILE.write_text(json.dumps(command_data))
                    print(f"✅ Relayed 'analyze_screenshot' command for path: {full_screenshot_path}")
                
                elif message_type == 'analyze_text_prompt':
                    prompt = data.get('prompt', 'No prompt provided.')
                    
                    command_data = {
                        "command": "analyze_text_prompt",
                        "prompt": prompt
                    }
                    COMMAND_FILE.write_text(json.dumps(command_data))
                    print(f"✅ Relayed 'analyze_text_prompt' command.")

                elif message_type == 'gemini_coach_request':
                    text = data.get('text', '')
                    if text:
                        command_data = {
                            "command": "gemini_coach_request",
                            "text": text
                        }
                        COMMAND_FILE.write_text(json.dumps(command_data))
                        print(f"✅ Relayed 'gemini_coach_request' command.")

                elif message_type == 'code_generation_request':
                    action = data.get('action')  # 'new_code' or 'update_code'
                    prompt = data.get('prompt', '')
                    transcripts = data.get('transcripts', '')

                    if action in ['new_code', 'update_code']:
                        command_data = {
                            "command": "code_generation_request",
                            "action": action,
                            "prompt": prompt,
                            "transcripts": transcripts
                        }
                        COMMAND_FILE.write_text(json.dumps(command_data))
                        print(f"✅ Relayed 'code_generation_request' command with action: {action}")
                    else:
                        print(f"⚠️  Invalid code generation action: {action}")

                elif message_type == 'mute_toggle':
                    muted = data.get('muted', False)
                    command_data = {
                        "command": "mute_toggle",
                        "muted": muted
                    }
                    COMMAND_FILE.write_text(json.dumps(command_data))
                    print(f"🔇 Transcriptions {'muted' if muted else 'unmuted'}")

            except json.JSONDecodeError:
                print(f"Received non-JSON message: {message_text}")
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connected_clients.discard(websocket)


def start_server(host="0.0.0.0", port=5000):
    """Start the web server and file watcher"""

    # Ensure generated_code directory exists
    GENERATED_CODE_DIR.mkdir(exist_ok=True)

    # Set up file watcher
    event_handler = CodeFileHandler(broadcast_to_clients)
    observer = Observer()
    observer.schedule(event_handler, str(GENERATED_CODE_DIR), recursive=False)
    observer.start()

    print(f"\n🌐 Web viewer running at http://{host}:{port}")
    print(f"   Open this URL in your browser to view generated code")
    print(f"   Press F9 in the browser to toggle semi-transparent overlay mode\n")

    try:
        uvicorn.run(app, host=host, port=port, log_level="error")
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    # Fix Windows console encoding for emojis
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    start_server()
