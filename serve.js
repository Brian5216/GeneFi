const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const STATIC_DIR = path.join(__dirname, 'static');
const BACKEND = {
  host: process.env.BACKEND_HOST || '127.0.0.1',
  port: parseInt(process.env.BACKEND_PORT || '8001'),
};
const PORT = parseInt(process.env.PORT || '8000');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

// HTTP server for static files and API proxy
const server = http.createServer((req, res) => {
  // Proxy API to Python backend
  if (req.url.startsWith('/api/')) {
    const proxy = http.request(
      { hostname: BACKEND.host, port: BACKEND.port, path: req.url, method: req.method, headers: req.headers },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
      }
    );
    proxy.on('error', () => { res.writeHead(502); res.end('Backend unavailable'); });
    req.pipe(proxy);
    return;
  }

  // Static files
  let filePath = req.url === '/' ? '/index.html' : req.url.split('?')[0];
  if (filePath.startsWith('/static/')) filePath = filePath.slice(7);
  const fullPath = path.join(STATIC_DIR, filePath);

  if (!fullPath.startsWith(STATIC_DIR)) { res.writeHead(403); res.end(); return; }

  fs.readFile(fullPath, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not Found'); return; }
    const ext = path.extname(fullPath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
});

// WebSocket proxy: application-level relay
const wss = new WebSocket.Server({ server, path: '/ws' });

wss.on('connection', (clientWs, req) => {
  console.log('[WS] Client connected, proxying to backend');

  const backendUrl = `ws://${BACKEND.host}:${BACKEND.port}/ws`;
  const backendWs = new WebSocket(backendUrl);
  let backendReady = false;
  const pendingMessages = [];

  backendWs.on('open', () => {
    console.log('[WS] Backend connected');
    backendReady = true;
    // Flush any queued messages
    for (const msg of pendingMessages) {
      console.log('[WS] Flushing queued msg:', msg.slice(0, 80));
      backendWs.send(msg);
    }
    pendingMessages.length = 0;
  });

  // Relay: backend -> client
  backendWs.on('message', (data) => {
    if (clientWs.readyState === WebSocket.OPEN) {
      clientWs.send(data.toString());
    }
  });

  // Relay: client -> backend (with buffering)
  clientWs.on('message', (data) => {
    const msg = data.toString();
    console.log('[WS] Client -> Backend:', msg.slice(0, 100));
    if (backendReady && backendWs.readyState === WebSocket.OPEN) {
      backendWs.send(msg);
    } else {
      console.log('[WS] Backend not ready, queuing message');
      pendingMessages.push(msg);
    }
  });

  backendWs.on('close', () => {
    console.log('[WS] Backend disconnected');
    if (clientWs.readyState === WebSocket.OPEN) clientWs.close();
  });

  clientWs.on('close', () => {
    console.log('[WS] Client disconnected');
    if (backendWs.readyState === WebSocket.OPEN) backendWs.close();
  });

  backendWs.on('error', (err) => {
    console.error('[WS] Backend error:', err.message);
    if (clientWs.readyState === WebSocket.OPEN) clientWs.close();
  });

  clientWs.on('error', (err) => {
    console.error('[WS] Client error:', err.message);
    if (backendWs.readyState === WebSocket.OPEN) backendWs.close();
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`GeneFi server on http://0.0.0.0:${PORT}`);
  console.log(`API/WS proxy -> Python backend :${BACKEND.port}`);
});
