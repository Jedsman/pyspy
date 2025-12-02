const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const { Monitor } = require('node-screenshots');
// Load environment variables from .env file in the same directory as main.js
require('dotenv').config({ path: path.join(__dirname, '.env') });

let mainWindow;
let screenshotWindow = null;

function createWindow() {
  // Get primary display dimensions
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  // Window dimensions
  const windowWidth = 800;
  const windowHeight = 600;
  const x = screenWidth - windowWidth - 20;
  const y = 20;

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: x,
    y: y,
    transparent: true,  // Enable transparency
    frame: false,       // Frameless for true transparency on Windows
    alwaysOnTop: true,  // Always on top
    resizable: true,    // Allow window resizing
    minWidth: 400,      // Minimum width
    minHeight: 300,     // Minimum height
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    backgroundColor: '#00000000'  // Fully transparent background
  });

  mainWindow.loadFile('overlay.html');

  // Optional: Open DevTools for debugging
  mainWindow.webContents.openDevTools();

  // Send default server IP to renderer once page is loaded
  mainWindow.webContents.on('did-finish-load', () => {
    const defaultServerIP = process.env.DEFAULT_SERVER_IP || 'localhost';
    mainWindow.webContents.send('set-default-server-ip', defaultServerIP);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC handler for setting mouse event forwarding
ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (window) {
    window.setIgnoreMouseEvents(ignore, options);
  }
});

// IPC handler for window resizing
ipcMain.on('resize-window', (event, deltaX, deltaY) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (window) {
    const [currentWidth, currentHeight] = window.getSize();
    const newWidth = Math.max(400, currentWidth + deltaX);
    const newHeight = Math.max(300, currentHeight + deltaY);
    window.setSize(newWidth, newHeight);
  }
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
      nodeIntegration: false,
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
    // Get the primary display dimensions
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width, height } = primaryDisplay.size;

    console.log(`Display info: logical=${width}x${height}`);
    console.log(`Selection: x=${selection.x}, y=${selection.y}, width=${selection.width}, height=${selection.height}`);

    // Use node-screenshots to capture the full screen at native resolution
    // This uses Windows DXGI API directly for maximum quality
    const monitors = Monitor.all();
    const primaryMonitor = monitors[0]; // Get primary monitor

    // Capture the entire screen at native resolution
    const fullScreenImage = primaryMonitor.captureImageSync();

    // Get the actual captured dimensions (width and height are properties, not methods)
    const capturedWidth = fullScreenImage.width;
    const capturedHeight = fullScreenImage.height;
    console.log(`Captured at native resolution: ${capturedWidth}x${capturedHeight}`);

    // Calculate the scale factor between logical and captured resolution
    const scaleX = capturedWidth / width;
    const scaleY = capturedHeight / height;

    // Scale the selection rectangle to match the captured resolution
    const scaledSelection = {
      x: Math.round(selection.x * scaleX),
      y: Math.round(selection.y * scaleY),
      width: Math.round(selection.width * scaleX),
      height: Math.round(selection.height * scaleY)
    };

    console.log(`Scaled selection: x=${scaledSelection.x}, y=${scaledSelection.y}, width=${scaledSelection.width}, height=${scaledSelection.height}`);

    // Crop the image to the selected area (using synchronous method)
    const croppedImage = fullScreenImage.cropSync(
      scaledSelection.x,
      scaledSelection.y,
      scaledSelection.width,
      scaledSelection.height
    );

    // Convert to PNG buffer (lossless quality)
    const pngBuffer = croppedImage.toPngSync();

    // Convert to base64 data URL
    const base64Data = pngBuffer.toString('base64');
    const pngDataUrl = `data:image/png;base64,${base64Data}`;

    console.log(`Cropped image size: ${croppedImage.width}x${croppedImage.height}`);

    // NOW, after the capture is complete, show the main window.
    if (mainWindow) {
      mainWindow.show();
    }

    // Send the captured image data back to the main window's renderer.
    mainWindow.webContents.send('screenshot-captured', { dataUrl: pngDataUrl, selection });

  } catch (e) {
    console.error('Failed to capture screen:', e);
    // Ensure the main window is shown even if capture fails.
    if (mainWindow) mainWindow.show();
    mainWindow.webContents.send('screenshot-captured', { dataUrl: null });
  }
});

// 3. Save the captured data URL to a file
ipcMain.handle('save-screenshot-data', async (event, dataUrl, promptText) => {
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

    // If promptText is provided, save it as a .txt metadata file AND add to prompt queue
    if (promptText) {
      const metadataFileName = `capture-${timestamp}.txt`;
      const metadataFilePath = path.join(screenshotsDir, metadataFileName);
      fs.writeFileSync(metadataFilePath, promptText, 'utf-8');
      console.log(`Saved prompt metadata: ${metadataFileName}`);

      // Add to MCP prompt queue for automated analysis
      const queueFilePath = path.join(screenshotsDir, '..', '.prompt_queue.json');
      let queue = [];
      if (fs.existsSync(queueFilePath)) {
        const queueData = fs.readFileSync(queueFilePath, 'utf-8');
        queue = JSON.parse(queueData);
      }

      queue.push({
        filename: fileName,
        prompt: promptText,
        timestamp: new Date().toISOString()
      });

      fs.writeFileSync(queueFilePath, JSON.stringify(queue, null, 2), 'utf-8');
      console.log(`Added to MCP prompt queue: ${fileName}`);
    }

    return { success: true, fileName: fileName, path: filePath }; // Return both for flexibility
  } catch (error) {
    console.error('Failed to save screenshot:', error);
    return { success: false, error: error.message };
  }
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
