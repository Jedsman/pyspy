# Electron Transparent Overlay Viewer

A true transparent overlay viewer for Voice-to-Code with **opaque text on transparent background**.

## Features

✅ **True Per-Element Transparency** - Text is fully opaque, only background is transparent
✅ **Adjustable Background Opacity** - Slider controls background transparency (0-90%)
✅ **Always On Top** - Floats over all windows
✅ **Click-Through Code Display** - Code area is transparent to mouse input, allowing interaction with apps underneath
✅ **Interactive Controls** - Title bar, controls, and tabs remain fully interactive
✅ **Real-time Updates** - WebSocket connection to web server
✅ **Full Syntax Highlighting** - Prism.js for all languages
✅ **Modern UI** - Blur effects and smooth controls
✅ **Draggable** - Reposition anywhere on screen
✅ **Remote Connection** - Connect to any server on your network

## Installation

1. Install Node.js if you don't have it: https://nodejs.org/

2. Open a terminal in the `electron-overlay` folder:
   ```bash
   cd electron-overlay
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

## Usage

1. Make sure the web server is running:
   ```bash
   python voice_to_code.py
   ```
   Or manually:
   ```bash
   python web_server.py
   ```

2. Start the Electron overlay:
   ```bash
   npm start
   ```

3. The overlay window will appear in the top-right corner

## Controls

- **🆕 New File Button** - Trigger generation of a new code file (same as hotkey)
- **💾 Update File Button** - Update the currently active file (same as hotkey)
- **BG Slider** - Adjust background opacity (0-90%)
- **Text Slider** - Adjust text opacity (30-100%)
- **🔗 Sync Button** - Toggle synchronized opacity control
- **Server Input** - Enter hostname/IP to connect to remote server
- **Connect Button** - Reconnect to server
- **Tab System** - Click tabs to switch files, × to close
- **ESC Key** - Close window
- **Drag Title Bar** - Move window anywhere

## How It Works

The overlay uses Electron's `transparent: true` window option combined with CSS and dynamic click-through:

**Visual Transparency:**
- `body { background: transparent }` - Fully transparent body
- `.header { background: rgba(10, 10, 10, 0.3) }` - Semi-transparent backgrounds
- `backdrop-filter: blur(10px)` - Modern blur effect (like macOS)
- Text remains fully opaque with `color: #ffffff`
- The slider adjusts only the `rgba()` alpha value of backgrounds, not the text

**Click-Through Functionality:**
- Uses Electron's `setIgnoreMouseEvents(true, { forward: true })` API
- JavaScript tracks mouse position in real-time
- When mouse is over code display area, window becomes click-through
- When mouse is over title bar, controls, or tabs, window captures mouse events
- Allows viewing code while interacting with applications underneath

## Comparison with Tkinter Viewer

| Feature | Tkinter | Electron |
|---------|---------|----------|
| Background transparency | Window-level only | Per-element ✓ |
| Text opacity | Fades with window | Always opaque ✓ |
| Click-through code area | No | Yes ✓ |
| Syntax highlighting | Basic Python | Full Prism.js ✓ |
| Dependencies | None (built-in) | Node.js + Electron |
| Size | ~300 lines Python | ~200 lines JS/HTML |
| Blur effects | No | Yes ✓ |

## Troubleshooting

### "npm: command not found"
- Install Node.js from https://nodejs.org/

### Port 5000 connection refused
- Ensure web server is running: `python web_server.py`
- Check server address in the input field

### Window not transparent on Linux
- Some Linux window managers don't support transparency
- Try installing `xcompmgr` or enable compositing in your WM

## Building Standalone Executable (Optional)

To create a standalone `.exe` (no Node.js required):

```bash
npm install electron-builder --save-dev
npx electron-builder --win
```

The executable will be in `dist/` folder (~150MB).
