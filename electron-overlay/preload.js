const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  setIgnoreMouseEvents: (ignore, options) => {
    ipcRenderer.send('set-ignore-mouse-events', ignore, options);
  },
  resizeWindow: (deltaX, deltaY) => {
    ipcRenderer.send('resize-window', deltaX, deltaY);
  },
  startScreenshot: () => {
    ipcRenderer.send('start-screenshot');
  },
  closeScreenshot: (selectionData) => {
    ipcRenderer.send('close-screenshot', selectionData);
  },
  onScreenshotCaptured: (callback) => {
    ipcRenderer.on('screenshot-captured', (event, data) => callback(data));
  },
  // Expose the new save function
  saveScreenshotData: (dataUrl) => ipcRenderer.invoke('save-screenshot-data', dataUrl)
});
