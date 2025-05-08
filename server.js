const http = require('http');
const fs = require('fs');
const path = require('path');

const port = 8000;
const base = __dirname;

http.createServer((req, res) => {
  let filePath = path.join(base, req.url === '/' ? '/index.html' : req.url);
  let ext = path.extname(filePath).toLowerCase();
  let type = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.png': 'image/png'
  }[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404); res.end('Not found');
    } else {
      res.writeHead(200, {'Content-Type': type});
      res.end(data);
    }
  });
}).listen(port, () => {
  console.log(`Server running at http://localhost:${port}/`);
});