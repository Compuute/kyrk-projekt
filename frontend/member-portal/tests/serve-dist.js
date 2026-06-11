// Static server for dist/ that mimics Cloudflare Pages URL semantics:
// /intake serves dist/intake/index.html directly (no 301 to /intake/),
// so relative links like "./" and "./churches/..." resolve the same way
// as on the deployed site. Plain `http-server`/`serve` redirect to the
// trailing-slash URL, which breaks every relative link on subpages.
//
// Not covered here: the Cloudflare Pages Functions middleware
// (functions/_middleware.ts) — language-prefix redirects, KV config
// injection and link rewriting only exist on the deployed site.
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'dist');
const PORT = parseInt(process.env.PORT || '4173', 10);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml',
  '.webmanifest': 'application/manifest+json',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

http
  .createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    let file = path.normalize(path.join(ROOT, pathname));
    if (!file.startsWith(ROOT)) {
      res.writeHead(403);
      res.end();
      return;
    }
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
      file = path.join(file, 'index.html');
    }
    if (!fs.existsSync(file)) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('not found: ' + pathname);
      return;
    }
    res.writeHead(200, {
      'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream',
      'Cache-Control': 'no-store',
    });
    fs.createReadStream(file).pipe(res);
  })
  .listen(PORT, () => {
    console.log('serving ' + ROOT + ' on http://127.0.0.1:' + PORT);
  });
