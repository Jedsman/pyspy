"""
Transparent Overlay Viewer for Voice-to-Code
Displays generated code files in a transparent, always-on-top window
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import asyncio
import json
import websockets
import threading
from pathlib import Path
import os
from typing import Dict

class TransparentOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Voice-to-Code Overlay")

        # Make window transparent and always on top
        # Note: transparency affects entire window in tkinter
        self.root.attributes('-alpha', 0.85)  # 85% opacity
        self.root.attributes('-topmost', True)

        # Set window size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 800
        window_height = 600
        x = screen_width - window_width - 20
        y = 20
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Configure dark theme colors with higher contrast for readability
        # Background is darker to enhance see-through effect
        # Text is brighter to maintain readability despite window transparency
        bg_color = '#0a0a0a'  # Very dark background
        fg_color = '#ffffff'  # Bright white text for maximum contrast
        select_bg = '#264f78'

        self.root.configure(bg=bg_color)

        # Current files and active file
        self.files: Dict[str, str] = {}
        self.active_file = None

        # Create UI
        self._create_ui(bg_color, fg_color, select_bg)

        # WebSocket connection
        self.ws_thread = None
        self.running = True

        # Bind keys
        self.root.bind('<Escape>', lambda e: self.root.quit())
        self.server_entry.bind('<Return>', lambda e: self.reconnect())

        # Start WebSocket connection
        self.start_websocket()

    def _create_ui(self, bg_color, fg_color, select_bg):
        """Create the UI elements"""
        # Header frame
        header = tk.Frame(self.root, bg=bg_color, pady=5)
        header.pack(fill=tk.X)

        # Title
        title = tk.Label(
            header,
            text="🎙️ Voice-to-Code Overlay",
            bg=bg_color,
            fg=fg_color,
            font=('Segoe UI', 12, 'bold')
        )
        title.pack(side=tk.LEFT, padx=10)

        # Status indicator
        self.status_label = tk.Label(
            header,
            text="● Connected",
            bg=bg_color,
            fg='#4caf50',
            font=('Segoe UI', 10)
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Server URL entry
        url_frame = tk.Frame(header, bg=bg_color)
        url_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(
            url_frame,
            text="Server:",
            bg=bg_color,
            fg=fg_color,
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.server_var = tk.StringVar(value=os.getenv("OVERLAY_SERVER", "localhost"))
        self.server_entry = tk.Entry(
            url_frame,
            textvariable=self.server_var,
            bg='#1a1a1a',
            fg=fg_color,
            insertbackground=fg_color,
            relief=tk.FLAT,
            width=20,
            font=('Consolas', 9)
        )
        self.server_entry.pack(side=tk.LEFT, padx=5)

        self.connect_btn = tk.Button(
            url_frame,
            text="Connect",
            bg='#0e639c',
            fg='#ffffff',
            activebackground='#1177bb',
            activeforeground='#ffffff',
            relief=tk.FLAT,
            font=('Segoe UI', 9),
            cursor='hand2',
            command=self.reconnect
        )
        self.connect_btn.pack(side=tk.LEFT)

        # Opacity slider
        opacity_frame = tk.Frame(header, bg=bg_color)
        opacity_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(
            opacity_frame,
            text="Opacity:",
            bg=bg_color,
            fg=fg_color,
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.opacity_var = tk.IntVar(value=50)  # 50% default for better see-through
        self.opacity_slider = tk.Scale(
            opacity_frame,
            from_=20,
            to=95,
            orient=tk.HORIZONTAL,
            variable=self.opacity_var,
            command=self.update_opacity,
            bg='#2d2d30',
            fg=fg_color,
            activebackground='#3e3e42',
            troughcolor='#0a0a0a',
            highlightthickness=0,
            length=150,
            width=15,
            font=('Segoe UI', 8),
            showvalue=True
        )
        self.opacity_slider.pack(side=tk.LEFT)

        # Controls hint
        controls = tk.Frame(header, bg=bg_color)
        controls.pack(side=tk.RIGHT, padx=10)

        tk.Label(
            controls,
            text="ESC: Close",
            bg=bg_color,
            fg='#858585',
            font=('Segoe UI', 9)
        ).pack()

        # Tab selector (Combobox)
        self.tab_var = tk.StringVar()
        self.tab_selector = ttk.Combobox(
            self.root,
            textvariable=self.tab_var,
            state='readonly',
            font=('Consolas', 10)
        )
        self.tab_selector.pack(fill=tk.X, padx=5, pady=5)
        self.tab_selector.bind('<<ComboboxSelected>>', self.on_tab_change)

        # Code display area
        code_frame = tk.Frame(self.root, bg=bg_color)
        code_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Text widget with scrollbar
        self.code_text = scrolledtext.ScrolledText(
            code_frame,
            bg='#0a0a0a',  # Very dark background
            fg='#ffffff',  # Bright white text
            insertbackground='#ffffff',
            selectbackground=select_bg,
            font=('Consolas', 10),
            wrap=tk.NONE,
            state=tk.DISABLED,
            relief=tk.FLAT,
            borderwidth=0
        )
        self.code_text.pack(fill=tk.BOTH, expand=True)

        # Configure syntax highlighting tags
        self._configure_syntax_tags()

    def _configure_syntax_tags(self):
        """Configure basic syntax highlighting colors - brighter for better visibility"""
        self.code_text.tag_configure('keyword', foreground='#6eb7ff')  # Brighter blue
        self.code_text.tag_configure('string', foreground='#f5a97f')  # Brighter orange
        self.code_text.tag_configure('comment', foreground='#7fb972')  # Brighter green
        self.code_text.tag_configure('function', foreground='#ffed8b')  # Brighter yellow
        self.code_text.tag_configure('number', foreground='#d4f5a7')  # Brighter number green

    def update_opacity(self, value=None):
        """Update window opacity from slider"""
        opacity = self.opacity_var.get() / 100.0
        self.root.attributes('-alpha', opacity)

    def on_tab_change(self, event=None):
        """Handle tab selection change"""
        filename = self.tab_var.get()
        if filename in self.files:
            self.active_file = filename
            self.display_file(filename, self.files[filename])

    def display_file(self, filename: str, content: str):
        """Display file content with basic syntax highlighting"""
        self.code_text.config(state=tk.NORMAL)
        self.code_text.delete('1.0', tk.END)

        # Add line numbers and content
        lines = content.split('\n')
        max_line_num = len(lines)
        line_num_width = len(str(max_line_num))

        for i, line in enumerate(lines, 1):
            line_num = f"{i:>{line_num_width}} │ "
            self.code_text.insert(tk.END, line_num, 'line_number')
            self.code_text.insert(tk.END, line + '\n')

        # Apply basic syntax highlighting for Python files
        if filename.endswith('.py'):
            self._highlight_python()

        self.code_text.config(state=tk.DISABLED)

    def _highlight_python(self):
        """Basic Python syntax highlighting"""
        keywords = ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif',
                   'for', 'while', 'try', 'except', 'with', 'as', 'pass', 'break',
                   'continue', 'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is']

        content = self.code_text.get('1.0', tk.END)

        # Highlight keywords
        for keyword in keywords:
            start = '1.0'
            while True:
                pos = self.code_text.search(rf'\b{keyword}\b', start, tk.END, regexp=True)
                if not pos:
                    break
                end = f"{pos}+{len(keyword)}c"
                self.code_text.tag_add('keyword', pos, end)
                start = end

        # Highlight strings
        for quote in ['"', "'"]:
            start = '1.0'
            while True:
                pos = self.code_text.search(quote, start, tk.END)
                if not pos:
                    break
                # Find closing quote
                end_pos = self.code_text.search(quote, f"{pos}+1c", tk.END)
                if end_pos:
                    self.code_text.tag_add('string', pos, f"{end_pos}+1c")
                    start = f"{end_pos}+1c"
                else:
                    break

        # Highlight comments
        start = '1.0'
        while True:
            pos = self.code_text.search('#', start, tk.END)
            if not pos:
                break
            # Comment until end of line
            line_end = self.code_text.index(f"{pos} lineend")
            self.code_text.tag_add('comment', pos, line_end)
            start = f"{pos}+1l"

        # Configure line number tag - brighter for visibility
        self.code_text.tag_configure('line_number', foreground='#a0a0a0')

    def update_file(self, filename: str, content: str):
        """Update a file in the display"""
        self.files[filename] = content

        # Update tab selector
        self.tab_selector['values'] = list(self.files.keys())

        # If this is the active file, update display
        if self.active_file == filename or self.active_file is None:
            self.active_file = filename
            self.tab_var.set(filename)
            self.display_file(filename, content)

    def set_status(self, status: str, color: str):
        """Update connection status"""
        self.status_label.config(text=f"● {status}", fg=color)

    def reconnect(self):
        """Reconnect to server with new URL"""
        # Stop current connection
        self.running = False
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1)

        # Restart with new server
        self.running = True
        self.start_websocket()

    async def websocket_client(self):
        """Connect to WebSocket server and receive updates"""
        # Get server from entry field
        server_host = self.server_var.get() or "localhost"
        uri = f"ws://{server_host}:5000/ws"
        retry_delay = 3

        while self.running:
            try:
                self.root.after(0, self.set_status, "Connecting...", "#ffa500")

                async with websockets.connect(uri) as websocket:
                    self.root.after(0, self.set_status, "Connected", "#4caf50")

                    async for message in websocket:
                        if not self.running:
                            break

                        try:
                            data = json.loads(message)
                            filename = data.get('filename')
                            content = data.get('content')

                            if filename and content:
                                # Update UI from main thread
                                self.root.after(0, self.update_file, filename, content)

                        except json.JSONDecodeError:
                            print(f"Failed to decode message: {message}")

            except Exception as e:
                self.root.after(0, self.set_status, "Disconnected", "#f44336")
                print(f"WebSocket error: {e}")
                if self.running:
                    await asyncio.sleep(retry_delay)

    def start_websocket(self):
        """Start WebSocket client in background thread"""
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.websocket_client())

        self.ws_thread = threading.Thread(target=run_async_loop, daemon=True)
        self.ws_thread.start()

    def run(self):
        """Start the overlay window"""
        try:
            self.root.mainloop()
        finally:
            self.running = False


def main():
    """Main entry point"""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    print("🌐 Starting transparent overlay viewer...")
    print("   Connecting to http://localhost:5000")
    print("   Press F9 to toggle transparency")
    print("   Press ESC to close\n")

    overlay = TransparentOverlay()
    overlay.run()


if __name__ == "__main__":
    main()
