const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const screenshot = require('screenshot-desktop');
const sharp = require('sharp');
// Load environment variables from .env file in the same directory as main.js
require('dotenv').config({ path: path.join(__dirname, '.env') });

let mainWindow;
let screenshotWindow;
let transcriptWindow;

// Helper function to send commands to the backend via HTTP
function sendCommandToBackend(command) {
    const postData = JSON.stringify({ command: command });

    const options = {
        hostname: 'localhost',
        port: 5000,
        path: '/api/command/transcript_window',
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        }
    };

    const req = http.request(options, (res) => {
        if (res.statusCode === 200) {
            console.log(`Command '${command}' sent successfully`);
        } else {
            console.log(`Failed to send command '${command}': ${res.statusCode}`);
        }
    });

    req.on('error', (e) => {
        console.error(`Error sending command '${command}':`, e.message);
    });

    req.write(postData);
    req.end();
}

function createTranscriptWindow() {
    if (transcriptWindow) {
        transcriptWindow.focus();
        return;
    }

    transcriptWindow = new BrowserWindow({
        width: 400,
        height: 700,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });

    transcriptWindow.loadFile('transcription_window.html');
    // transcriptWindow.webContents.openDevTools({ mode: 'detach' });

    // Notify backend that transcript window is opened
    transcriptWindow.once('ready-to-show', () => {
        sendCommandToBackend('transcript_window_opened');
    });

    transcriptWindow.on('closed', () => {
        // Notify backend that transcript window is closed
        sendCommandToBackend('transcript_window_closed');
        transcriptWindow = null;
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 600,
        frame: false,
        transparent: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        alwaysOnTop: true,
    });

    mainWindow.loadFile('overlay.html');

    // Press F12 to toggle DevTools
    mainWindow.webContents.on('before-input-event', (event, input) => {
        if (input.key === 'F12' && input.type === 'keyDown') {
            if (mainWindow.webContents.isDevToolsOpened()) {
                mainWindow.webContents.closeDevTools();
            } else {
                mainWindow.webContents.openDevTools({ mode: 'detach' });
            }
        }
    });
}

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// === IPC Handlers ===

// Handle window resizing from renderer
ipcMain.on('resize-window', (event, deltaX, deltaY) => {
    if (mainWindow) {
        const bounds = mainWindow.getBounds();
        const newWidth = Math.max(600, bounds.width + deltaX);  // Minimum width: 600px
        const newHeight = Math.max(400, bounds.height + deltaY);  // Minimum height: 400px

        mainWindow.setBounds({
            x: bounds.x,
            y: bounds.y,
            width: newWidth,
            height: newHeight
        });
    }
});

// Handle setting mouse event forwarding
ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
    if (mainWindow) {
        mainWindow.setIgnoreMouseEvents(ignore, options);
    }
});

ipcMain.on('open-transcript-window', () => {
    createTranscriptWindow();
});

ipcMain.handle('get-default-server-ip', () => {
    return process.env.DEFAULT_SERVER_IP || 'localhost';
});

// --- Screenshot Flow ---

// 1. Start the screenshot process
ipcMain.on('start-screenshot', () => {
    if (mainWindow) {
        mainWindow.hide();
    }

    const primaryDisplay = screen.getPrimaryDisplay();
    const { width, height } = primaryDisplay.size;

    screenshotWindow = new BrowserWindow({
        width,
        height,
        x: 0,
        y: 0,
        frame: false,
        transparent: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
        },
        fullscreen: true,
        alwaysOnTop: true,
    });

    screenshotWindow.loadFile('screenshot.html');
});

// 2. Close the screenshot window and capture the screen
ipcMain.on('close-screenshot', async (event, selection) => {
    // Close the transparent screenshot window first
    if (screenshotWindow) {
        screenshotWindow.close();
        screenshotWindow = null;
    }

    // If no selection was made (e.g., user pressed ESC), do nothing further.
    if (!selection) {
        if (mainWindow) mainWindow.show(); // Show the window on cancellation.
        mainWindow.webContents.send('screenshot-captured', null);
        return;
    }

    try {
        // Get the primary display dimensions and DPI
        const primaryDisplay = screen.getPrimaryDisplay();
        const { width: logicalWidth, height: logicalHeight } = primaryDisplay.size;
        const scaleFactor = primaryDisplay.scaleFactor;

        console.log(`📸 Display: logical=${logicalWidth}x${logicalHeight}, DPI scale=${scaleFactor}`);
        console.log(`📸 Selection: x=${selection.x}, y=${selection.y}, width=${selection.width}, height=${selection.height}`);

        // Capture full screen at native resolution
        const fullScreenBuffer = await screenshot();
        console.log(`📸 Full screen captured: ${(fullScreenBuffer.length / 1024 / 1024).toFixed(2)} MB`);

        // Calculate native resolution coordinates from logical coordinates
        const nativeX = Math.round(selection.x * scaleFactor);
        const nativeY = Math.round(selection.y * scaleFactor);
        const nativeWidth = Math.round(selection.width * scaleFactor);
        const nativeHeight = Math.round(selection.height * scaleFactor);

        console.log(`📸 Cropping at native resolution: ${nativeWidth}x${nativeHeight} at (${nativeX}, ${nativeY})`);

        // Crop and convert to PNG with text-optimized settings
        const croppedBuffer = await sharp(fullScreenBuffer)
            .extract({
                left: nativeX,
                top: nativeY,
                width: nativeWidth,
                height: nativeHeight
            })
            .sharpen()  // Enhance text clarity and edges
            .png({
                compressionLevel: 9,      // Maximum compression for smaller files
                adaptiveFiltering: true   // Better quality at high compression
            })
            .toBuffer();

        console.log(`📸 Cropped image: ${(croppedBuffer.length / 1024).toFixed(2)} KB`);

        const croppedBase64 = croppedBuffer.toString('base64');
        const dataUrl = `data:image/png;base64,${croppedBase64}`;

        // Show main window and send result
        if (mainWindow) {
            mainWindow.show();
        }

        mainWindow.webContents.send('screenshot-captured', { dataUrl, selection });

    } catch (e) {
        console.error('❌ Screenshot capture failed:', e.message);
        if (mainWindow) mainWindow.show();
        mainWindow.webContents.send('screenshot-captured', { dataUrl: null });
    }
});


// 3. Save the captured data URL to a file
ipcMain.handle('save-screenshot-data', async (event, dataUrl, promptText, destinations) => {
    try {
        // Default to both destinations if not provided
        const dests = destinations || { gemini: true, claude: true };

        // Use the path from the .env file, or a default if not provided.
        const screenshotsDir = process.env.SCREENSHOT_PATH || path.join(__dirname, '..', 'generated_code', 'screenshots');
        const generatedCodeDir = path.dirname(screenshotsDir);

        if (!fs.existsSync(screenshotsDir)) {
            fs.mkdirSync(screenshotsDir, { recursive: true });
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const fileName = `capture-${timestamp}.png`;
        const filePath = path.join(screenshotsDir, fileName);
        const data = Buffer.from(dataUrl.split(',')[1], 'base64');

        fs.writeFileSync(filePath, data);

        // If a prompt is provided, save it as a text file alongside the screenshot
        if (promptText) {
            const promptFileName = `capture-${timestamp}.txt`;
            const promptFilePath = path.join(screenshotsDir, promptFileName);
            fs.writeFileSync(promptFilePath, promptText, 'utf-8');
            console.log(`Saved prompt metadata: ${promptFileName}`);

            // Write to .command file for Gemini if enabled
            if (dests.gemini) {
                const commandFilePath = path.join(generatedCodeDir, '.command');
                const commandData = {
                    command: 'analyze_screenshot',
                    prompt: promptText,
                    screenshot_path: filePath
                };
                fs.writeFileSync(commandFilePath, JSON.stringify(commandData), 'utf-8');
                console.log('Added to .command file: analyze_screenshot');
            }

            // Add to .prompt_queue.json for Claude Desktop MCP server if enabled
            if (dests.claude) {
                const queueFilePath = path.join(generatedCodeDir, '.prompt_queue.json');
                let queue = [];
                if (fs.existsSync(queueFilePath)) {
                    const queueData = fs.readFileSync(queueFilePath, 'utf-8');
                    queue = JSON.parse(queueData);
                }

                queue.push({
                    filename: fileName,
                    prompt: promptText,
                    timestamp: new Date().toISOString(),
                    type: 'screenshot'
                });

                fs.writeFileSync(queueFilePath, JSON.stringify(queue, null, 2), 'utf-8');
                console.log(`Added to .prompt_queue.json: ${fileName}`);
            }
        }

        return { success: true, fileName: fileName, path: filePath }; // Return both for flexibility
    } catch (error) {
        console.error('Failed to save screenshot:', error);
        return { success: false, error: error.message };
    }
});

// Handle adhoc text prompts (for 'copy' action prompts)
ipcMain.handle('send-adhoc-prompt', async (event, promptText, destinations) => {
    try {
        // Default to both destinations if not provided
        const dests = destinations || { gemini: true, claude: true };

        const generatedCodeDir = process.env.GENERATED_CODE_PATH || path.join(__dirname, '..', 'generated_code');

        // Write .command file for Gemini if enabled
        if (dests.gemini) {
            const commandFilePath = path.join(generatedCodeDir, '.command');
            const commandData = {
                command: 'analyze_text_prompt',
                prompt: promptText
            };
            fs.writeFileSync(commandFilePath, JSON.stringify(commandData), 'utf-8');
            console.log('Added to .command file: analyze_text_prompt');
        }

        // Append to .prompt_queue.json for Claude Desktop if enabled
        if (dests.claude) {
            const queueFilePath = path.join(generatedCodeDir, '.prompt_queue.json');
            let queue = [];
            if (fs.existsSync(queueFilePath)) {
                const queueData = fs.readFileSync(queueFilePath, 'utf-8');
                queue = JSON.parse(queueData);
            }

            queue.push({
                prompt: promptText,
                timestamp: new Date().toISOString(),
                type: 'adhoc'
            });

            fs.writeFileSync(queueFilePath, JSON.stringify(queue, null, 2), 'utf-8');
            console.log('Added to .prompt_queue.json: adhoc text prompt');
        }

        return { success: true };
    } catch (error) {
        console.error('Failed to send adhoc prompt:', error);
        return { success: false, error: error.message };
    }
});
