const { app, BrowserWindow, screen, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

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
