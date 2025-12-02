const { app, BrowserWindow, ipcMain, screen, desktopCapturer } = require('electron');
const path = require('path');
const fs = require('fs');
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
