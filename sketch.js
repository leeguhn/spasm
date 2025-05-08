// --- p5.js + WEBGL: Mesh + Voronoi + Keyboard Control ---

let cols = 20, rows_ = 14; // renamed 'rows' to 'rows_'
let mesh = [];
let nodes = [];
let keyToNode = {};

function windowResized() {
    resizeCanvas(windowWidth, windowHeight);
}

function setup() {
  createCanvas(windowWidth, windowHeight, WEBGL);

  // 1. Create mesh grid
  for (let y = 0; y < rows_; y++) {
    let meshRow = [];
    for (let x = 0; x < cols; x++) {
      meshRow.push({
        x: map(x, 0, cols-1, -400, 400),
        y: map(y, 0, rows_-1, -250, 250),
        vx: 0, vy: 0,
        rest_x: map(x, 0, cols-1, -400, 400),
        rest_y: map(y, 0, rows_-1, -250, 250)
      });
    }
    mesh.push(meshRow);
  }

  // 2. Create muscle nodes according to QWERTY layout
  const keyboardRows = [
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm"
  ];
  nodes = [];
  keyToNode = {};
  let totalRows = keyboardRows.length;
  for (let row = 0; row < totalRows; row++) {
    let keys = keyboardRows[row];
    let y = map(row, 0, totalRows - 1, -250, 250);
    for (let col = 0; col < keys.length; col++) {
      let x = map(col, 0, keys.length - 1, -400, 400);
      let key = keys[col];
      let node = { x, y, force: 0 };
      nodes.push(node);
      keyToNode[key] = nodes.length - 1;
    }
  }
}

function draw() {
  background(255);
  orbitControl();

  // --- Mesh physics ---
  for (let y = 0; y < rows_; y++) {
    for (let x = 0; x < cols; x++) {
      let p = mesh[y][x];
      // Spring to rest
      let fx = (p.rest_x - p.x) * 0.08;
      let fy = (p.rest_y - p.y) * 0.08;
      // Pull by muscle nodes
      for (let node of nodes) {
        let d = dist(p.x, p.y, node.x, node.y);
        if (node.force > 0 && d < 180) {
          let strength = 3 * node.force * (180 - d) / 180;
          fx += (node.x - p.x) * strength * 0.01;
          fy += (node.y - p.y) * strength * 0.01;
        }
      }
      p.vx = (p.vx + fx) * 0.88;
      p.vy = (p.vy + fy) * 0.88;
      p.x += p.vx;
      p.y += p.vy;
    }
  }

  // --- Voronoi: use muscle nodes as sites ---
  let voronoiSites = nodes.map(n => ({x: n.x, y: n.y}));
  let cellMap = {};
  let step = 16;
  for (let x = -400; x < 400; x += step) {
    for (let y = -250; y < 250; y += step) {
      let minD = 1e9, minIdx = -1;
      for (let i = 0; i < voronoiSites.length; i++) {
        let d = dist(x, y, voronoiSites[i].x, voronoiSites[i].y);
        if (d < minD) { minD = d; minIdx = i; }
      }
      if (!cellMap[minIdx]) cellMap[minIdx] = [];
      cellMap[minIdx].push([x, y]);
    }
  }

  // --- Draw mesh as lines ---
  stroke(0);
  noFill();
  for (let y = 0; y < rows_; y++) {
    beginShape();
    for (let x = 0; x < cols; x++) {
      vertex(mesh[y][x].x, mesh[y][x].y);
    }
    endShape();
  }
  for (let x = 0; x < cols; x++) {
    beginShape();
    for (let y = 0; y < rows_; y++) {
      vertex(mesh[y][x].x, mesh[y][x].y);
    }
    endShape();
  }

  // --- Draw dots at mesh intersection points with slight jitter ---
  noStroke();
  fill(0);
  for (let y = 0; y < rows_; y++) {
    for (let x = 0; x < cols; x++) {
      let p = mesh[y][x];
      // Add organic jitter using Perlin noise
      let jitterX = noise(p.x * 0.03, p.y * 0.03, frameCount * 0.01) * 2 - 1;
      let jitterY = noise(p.y * 0.03, p.x * 0.03, frameCount * 0.01) * 2 - 1;
      ellipse(p.x + jitterX, p.y + jitterY, 8, 8);
    }
  }

}

// --- Keyboard controls for muscle nodes ---
function keyPressed() {
  let k = key.toLowerCase();
  if (k in keyToNode) {
    nodes[keyToNode[k]].force = 1;
  }
}
function keyReleased() {
  let k = key.toLowerCase();
  if (k in keyToNode) {
    nodes[keyToNode[k]].force = 0;
  }
}