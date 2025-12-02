const { app, BrowserWindow, ipcMain, screen, desktopCapturer } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
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
        width: 800,
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
    // mainWindow.webContents.openDevTools({ mode: 'detach' });
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
        const [width, height] = mainWindow.getSize();
        mainWindow.setSize(width + deltaX, height + deltaY);
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
        // Get all available desktop sources (screens)
        const sources = await desktopCapturer.getSources({
            types: ['screen'],
            thumbnailSize: screen.getPrimaryDisplay().size // Capture at full resolution
        });

        // Find the source for the primary display.
        const primaryDisplay = screen.getPrimaryDisplay();
        const primarySource = sources.find(source => source.display_id === primaryDisplay.id.toString());

        if (!primarySource) {
            throw new Error('Primary display source not found.');
        }

        // Crop the full-screen thumbnail to the user's selection.
        const croppedImage = primarySource.thumbnail.crop(selection);
        const dataUrl = croppedImage.toDataURL();

        // NOW, after the capture is complete, show the main window.
        if (mainWindow) {
            mainWindow.show();
        }

        // Send the captured image data back to the main window's renderer.
        // Also include the original selection rectangle for context.
        mainWindow.webContents.send('screenshot-captured', { dataUrl, selection });

    } catch (e) {
        console.error('Failed to capture screen:', e);
        // Ensure the main window is shown even if capture fails.
        if (mainWindow) mainWindow.show();
        mainWindow.webContents.send('screenshot-captured', { dataUrl: null });
    }
});


// 3. Save the captured data URL to a file
ipcMain.handle('save-screenshot-data', async (event, dataUrl) => {
    try {
        // Use the path from the .env file, or a default if not provided.
        const screenshotsDir = process.env.SCREENSHOT_PATH || path.join(__dirname, '..', 'generated_code', 'screenshots');

        if (!fs.existsSync(screenshotsDir)) {
            fs.mkdirSync(screenshotsDir, { recursive: true });
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const fileName = `capture-${timestamp}.png`;
        const filePath = path.join(screenshotsDir, fileName);
        const data = Buffer.from(dataUrl.split(',')[1], 'base64');

        fs.writeFileSync(filePath, data);

        return { success: true, fileName: fileName, path: filePath }; // Return both for flexibility
    } catch (error) {
        console.error('Failed to save screenshot:', error);
        return { success: false, error: error.message };
    }
});
