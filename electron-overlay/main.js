const { app, BrowserWindow, screen, ipcMain, desktopCapturer } = require('electron');
const path = require('path');

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

// IPC handler for starting screenshot selection
ipcMain.on('start-screenshot', (event) => {
  if (screenshotWindow) return; // Already open

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.bounds;

  // Hide main window
  if (mainWindow) {
    mainWindow.hide();
  }

  // Create fullscreen screenshot window
  screenshotWindow = new BrowserWindow({
    width: width,
    height: height,
    x: 0,
    y: 0,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    fullscreen: true,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    backgroundColor: '#00000000'
  });

  screenshotWindow.loadFile('screenshot.html');

  screenshotWindow.on('closed', () => {
    screenshotWindow = null;
    // Show main window again
    if (mainWindow) {
      mainWindow.show();
    }
  });
});

// IPC handler for closing screenshot window and capturing the selected area
ipcMain.on('close-screenshot', async (event, selectionData) => {
  if (screenshotWindow) {
    screenshotWindow.close();
  }

  // If a selection was made, capture it
  if (mainWindow && selectionData) {
    try {
      const sources = await desktopCapturer.getSources({ types: ['screen'] });
      const primaryDisplaySource = sources.find(source => source.display_id === screen.getPrimaryDisplay().id.toString());

      if (primaryDisplaySource) {
        // The thumbnail is a full-sized nativeImage
        const screenshotImage = primaryDisplaySource.thumbnail;
        
        // Crop the image to the selected area
        // We need to account for device scale factor
        const scaleFactor = screen.getPrimaryDisplay().scaleFactor;
        const croppedImage = screenshotImage.crop({
          x: Math.floor(selectionData.x * scaleFactor),
          y: Math.floor(selectionData.y * scaleFactor),
          width: Math.floor(selectionData.width * scaleFactor),
          height: Math.floor(selectionData.height * scaleFactor)
        });

        // Convert to data URL to send to renderer process
        const dataUrl = croppedImage.toDataURL();
        
        // Send the captured image data back to the main window
        mainWindow.webContents.send('screenshot-captured', dataUrl);
      }
    } catch (e) {
      console.error('Failed to capture screenshot:', e);
    }
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
