const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('fairy', {
  send: message => ipcRenderer.send('fairy:send', message),
  sources: () => ipcRenderer.invoke('fairy:sources'),
  onEvent: callback => ipcRenderer.on('fairy:event', (_event, value) => callback(value)),
});
