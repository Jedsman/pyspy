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
  saveScreenshotData: (dataUrl, promptText, destinations) => ipcRenderer.invoke('save-screenshot-data', dataUrl, promptText, destinations),
  sendAdhocPrompt: (promptText, destinations) => ipcRenderer.invoke('send-adhoc-prompt', promptText, destinations),
  sendCodeGenerationRequest: (action, promptText, transcripts, destinations) => ipcRenderer.invoke('send-code-generation-request', action, promptText, transcripts, destinations),
  openTranscriptWindow: () => ipcRenderer.send('open-transcript-window'),
  getDefaultServerIp: () => ipcRenderer.invoke('get-default-server-ip')
});
