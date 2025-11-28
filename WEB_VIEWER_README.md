# Viewers for Voice-to-Code

Two options for viewing generated code files with live updates:
1. **Web Viewer** - Browser-based, works on any device on your network
2. **Overlay Viewer** - Transparent desktop app, always-on-top overlay

## Web Viewer Features

✅ **Real-time Updates** - Files appear instantly via WebSocket
✅ **Syntax Highlighting** - Automatic language detection with Prism.js
✅ **Tabbed Interface** - One tab per file, scrollable after 10 tabs
✅ **Line Numbers** - Easy reference for code review
✅ **Flash Animations** - Visual feedback when tabs update
✅ **Tab Management** - Close individual tabs with × button
✅ **Session Tracking** - Only shows files from current session
✅ **Update Indicator** - Shows "Updating..." when receiving changes
✅ **Scroll Position Preserved** - Stays at your position during updates
✅ **Remote Viewing** - View from any device on your network

## Overlay Viewer Features

✅ **True Transparency** - OS-level transparent window, see through to apps behind
✅ **Always On Top** - Floats over all other windows
✅ **Real-time Updates** - Files appear instantly via WebSocket
✅ **Syntax Highlighting** - Basic Python syntax highlighting
✅ **Line Numbers** - Easy reference for code review
✅ **Toggle Opacity** - Press F9 to adjust transparency (85% ↔ 95%)
✅ **Lightweight** - Uses tkinter (built into Python, no extra dependencies)
✅ **Auto-position** - Opens in top-right corner of screen

## Installation

### Web Viewer Dependencies

```bash
uv pip install fastapi uvicorn watchdog websockets
```

Or add to your `pyproject.toml`:
```toml
[project.optional-dependencies]
web = ["fastapi", "uvicorn", "watchdog", "websockets"]
```

Then install with:
```bash
uv sync --extra web
```

### Overlay Viewer Dependencies

**No extra dependencies needed!** Uses tkinter which is built into Python.

## Usage

### Web Viewer

#### Automatic Start (Default)

The web viewer starts automatically when you run `voice_to_code.py`:

```bash
python voice_to_code.py
```

The viewer will be available at: **http://localhost:5000**

#### Manual Start

If you prefer to run the web server separately:

1. Disable auto-start by setting in `.env`:
   ```
   ENABLE_WEB_VIEWER=false
   ```

2. Start the web server manually in a separate terminal:
   ```bash
   python web_server.py
   ```

3. Open http://localhost:5000 in your browser

### Overlay Viewer

Start the transparent overlay viewer in a separate terminal:

```bash
python overlay_viewer.py
```

The overlay window will:
- Open in the top-right corner of your screen
- Connect to http://localhost:5000 automatically
- Display generated code files in real-time
- Stay on top of all other windows
- Allow you to see through to applications behind it

**Note**: The overlay viewer connects to the web server, so make sure `voice_to_code.py` (with web viewer enabled) or `web_server.py` is running first.

### Remote Viewing

To view from another PC on your local network:

1. Find your PC's IP address:
   - Windows: `ipconfig` (look for IPv4 Address)
   - Linux/Mac: `ifconfig` or `ip addr`

2. On the remote PC, open: `http://YOUR_IP:5000`
   - Example: `http://192.168.1.100:5000`

3. **Security Note**: The server is open on your local network with no authentication. Only use on trusted networks.

## Controls

### Web Viewer Controls

- **🆕 New File Button** - Trigger generation of a new code file (same as Ctrl+Shift+G hotkey)
- **💾 Update File Button** - Update the currently active file (same as Ctrl+Shift+S hotkey)
- **Toggle Overlay (F9)** - Switch to semi-transparent mode
- **Click Tab** - Switch to that file
- **Click ×** - Close tab
- **Scroll Tabs** - Horizontal scroll when >10 tabs

### Overlay Viewer Controls

- **F9** - Toggle opacity (85% ↔ 95%)
- **ESC** - Close overlay window
- **Dropdown** - Select which file to view
- **Drag Window** - Reposition anywhere on screen

The overlay window is:
- **Always on top** - Floats over all applications
- **Truly transparent** - OS-level transparency lets you see through to apps behind
- **Lightweight** - Minimal resource usage
- **Auto-updating** - Files update in real-time via WebSocket

## How It Works

```
voice_to_code.py (main script)
    ↓ saves files to
generated_code/ folder
    ↓ watched by
web_server.py (FastAPI + watchdog)
    ↓ broadcasts via WebSocket
Browser @ http://localhost:5000
    ↓ displays in real-time tabs
```

**File Watcher** - Monitors `generated_code/` folder for changes
**WebSocket** - Instant push updates (no polling)
**Session Tracking** - Only files created during current session are shown

## Supported Languages

Automatic syntax highlighting for:
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts)
- Java (.java)
- C/C++ (.c, .cpp)
- Go (.go)
- Rust (.rs)
- Ruby (.rb)
- PHP (.php)
- HTML (.html)
- CSS (.css)
- SQL (.sql)
- Bash (.sh)
- JSON (.json)
- XML (.xml)
- Markdown (.md)

## Troubleshooting

### Port Already in Use

If you see "Port 5000 is already in use":
- Check if web_server.py is already running
- Close other applications using port 5000
- Or change the port in `web_server.py` (line: `start_server(port=5000)`)

### Files Not Appearing

1. Ensure `generated_code/` folder exists
2. Check that files were created AFTER the web server started
3. Refresh the browser page
4. Check browser console (F12) for errors

### Connection Lost

If the status indicator turns red:
- Web server may have crashed
- Check the terminal for error messages
- Restart the web server
- Browser will auto-reconnect in 3 seconds

### Overlay Viewer Not Connecting

If the overlay viewer shows "Disconnected":
- Ensure web server is running (`voice_to_code.py` or `python web_server.py`)
- Check that port 5000 is not blocked by firewall
- Verify http://localhost:5000 works in your browser first
- Overlay will auto-reconnect every 3 seconds

## Configuration

### Environment Variables

Add to `.env` file:

```bash
# Enable/disable web viewer auto-start (default: true)
ENABLE_WEB_VIEWER=true

# Load existing files when browser connects (default: true)
# Set to false to only show files created AFTER web server starts
LOAD_EXISTING_FILES=true
```

**LOAD_EXISTING_FILES Options:**
- `true` (default) - Shows all existing files in `generated_code/` folder when you open the browser
- `false` - Only shows files created after the web server starts (strict session-only mode)

### Customize Port/Host

Edit `web_server.py` at the bottom:

```python
if __name__ == "__main__":
    start_server(host="0.0.0.0", port=5000)  # Change port here
```

### Adjust Transparency

Edit the CSS in `web_server.py`, find:

```css
body.overlay-mode {
    background: rgba(30, 30, 30, 0.85);  /* Change 0.85 to your preference (0-1) */
}
```

## Architecture

### Components

1. **FastAPI Server** - HTTP and WebSocket endpoints
2. **Watchdog** - File system monitoring
3. **WebSocket Manager** - Broadcasts to connected clients
4. **HTML/CSS/JS Frontend** - Embedded in web_server.py
5. **Prism.js** - Syntax highlighting via CDN

### Data Flow

```
File Created/Modified
    → watchdog detects change
    → reads file content
    → detects language from extension
    → broadcasts JSON via WebSocket
    → browser receives update
    → creates/updates tab
    → applies syntax highlighting
    → flashes tab animation
```

## Future Enhancements

Potential features to add:
- [ ] Copy to clipboard button
- [ ] Download file button
- [ ] Search within files
- [ ] Diff view for updates
- [ ] Dark/light theme toggle
- [ ] Custom color schemes
- [ ] File history/versions
- [ ] Multi-user support with authentication
- [ ] Mobile-responsive design

## Support

For issues or questions:
1. Check the main `voice_to_code.py` logs
2. Check browser console (F12) for JavaScript errors
3. Verify all dependencies are installed
4. Ensure firewall allows port 5000 (for remote viewing)
