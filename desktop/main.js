const { app, BrowserWindow, ipcMain, desktopCapturer, session } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');

const root = path.resolve(__dirname, '..');
let window;
let backend;
let quitting = false;

function send(message) {
  if (backend && backend.stdin.writable) backend.stdin.write(JSON.stringify(message) + '\n');
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((_contents, permission, callback) => callback(permission === 'media'));
  window = new BrowserWindow({ width: 1080, height: 760, minWidth: 760, minHeight: 580,
    backgroundColor: '#111116', webPreferences: { preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false, sandbox: true } });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', event => event.preventDefault());
  window.loadFile(path.join(__dirname, 'index.html'));
  window.webContents.once('did-finish-load', startBackend);
});

function pythonPath() {
  const relative = ['.venv', 'Scripts', 'python.exe'];
  const candidates = [];
  if (process.env.FAIRY_ASSET_ROOT) candidates.push(path.resolve(process.env.FAIRY_ASSET_ROOT, ...relative));
  candidates.push(path.join(root, ...relative));
  try {
    // In a git worktree, .git is a file: "gitdir: <main>/.git/worktrees/<name>".
    const text = fs.readFileSync(path.join(root, '.git'), 'utf8');
    const match = /^gitdir:\s*(.+)$/m.exec(text);
    if (match) {
      const gitdir = path.resolve(root, match[1].trim());
      candidates.push(path.join(path.dirname(path.dirname(path.dirname(gitdir))), ...relative));
    }
  } catch {}
  return candidates.find(candidate => fs.existsSync(candidate)) ?? candidates[0];
}

function startBackend() {
  const python = pythonPath();
  backend = spawn(python, ['-u', '-m', 'fairy.desktop.bridge'], { cwd: root, windowsHide: true,
    env: { ...process.env, PYTHONUTF8: '1' }, stdio: ['pipe', 'pipe', 'pipe'] });
  backend.stdin.on('error', () => {});
  backend.stderr.on('data', chunk => process.stderr.write(chunk));
  backend.on('error', error => window?.webContents.send('fairy:event', { type: 'fatal', message: error.message }));
  backend.on('exit', code => { if (!quitting) window?.webContents.send('fairy:event', { type: 'fatal', message: `Backend stopped (${code}). Restart Fairy.` }); });
  readline.createInterface({ input: backend.stdout }).on('line', line => {
    try { const event = JSON.parse(line); window?.webContents.send('fairy:event', event); if (event.type === 'fatal') backend.stdin.end(); }
    catch { console.error('Invalid backend message'); }
  });
}

ipcMain.on('fairy:send', (event, message) => {
  if (event.sender === window?.webContents && message && typeof message === 'object') send(message);
});
ipcMain.handle('fairy:sources', async event => {
  if (event.sender !== window?.webContents) return [];
  const sources = await desktopCapturer.getSources({ types: ['screen', 'window'], thumbnailSize: { width: 180, height: 100 } });
  return sources.map(source => ({ id: source.id, name: source.name, thumbnail: source.thumbnail.toDataURL() }));
});
app.on('window-all-closed', () => app.quit());
app.on('before-quit', event => {
  if (quitting || !backend || backend.exitCode !== null) return;
  event.preventDefault();
  quitting = true;
  send({ type: 'shutdown' });
  backend.stdin.end();
  backend.once('exit', () => app.quit());
  setTimeout(() => { backend.kill(); app.quit(); }, 30000).unref();
});
