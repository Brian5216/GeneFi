import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STATIC_DIR = path.join(__dirname, 'static');
const BACKEND_PORT = 8001;
const PORT = 8000;

const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  // Proxy API requests to Python backend
  if (url.pathname.startsWith('/api/')) {
    const proxy = http.request(
      { hostname: '127.0.0.1', port: BACKEND_PORT, path: req.url, method: req.method, headers: req.headers },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
      }
    );
    proxy.on('error', () => {
      res.writeHead(502);
      res.end('Backend unavailable');
    });
    req.pipe(proxy);
    return;
  }

  // Static files
  let filePath = url.pathname === '/' ? '/index.html' : url.pathname;
  const fullPath = path.join(STATIC_DIR, filePath);

  if (!fullPath.startsWith(STATIC_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.readFile(fullPath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not Found');
      return;
    }
    const ext = path.extname(fullPath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
});

// WebSocket proxy
server.on('upgrade', (req, socket, head) => {
  if (req.url === '/ws') {
    const proxySocket = new (await import('node:net')).Socket();
    // Simple TCP proxy to backend WS
    const net = await import('node:net');
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`GeneFi proxy server on http://0.0.0.0:${PORT}`);
  console.log(`Proxying API to Python backend on port ${BACKEND_PORT}`);
});
