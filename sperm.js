let cols = 20, rows_ = 14;
let mesh = [];
let nodes = [];
let keyToNode = {};
let assets = [];
let assetCount = 50; // Set to your number of PNGs
let spermCells = [];

function preload() {
  for (let i = 0; i < assetCount; i++) {
    assets.push(loadImage('algo/line_' + i + '.png'));
  }
}

function setup() {
  createCanvas(900, 600, WEBGL);

  // 1. Create mesh grid (invisible substrate)
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

  // 3. Create sperm cells, one per asset, initially at mesh points
  spermCells = [];
  let idx = 0;
  for (let y = 0; y < rows_; y++) {
    for (let x = 0; x < cols; x++) {
      if (idx < assets.length) {
        let p = mesh[y][x];
        spermCells.push({
          x: p.x,
          y: p.y,
          vx: random(-1, 1),
          vy: random(-1, 1),
          img: assets[idx],
          meshIdx: {x, y}
        });
        idx++;
      }
    }
  }
}

function draw() {
  background(20);
  orbitControl();

  // --- Mesh physics (invisible) ---
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

  // --- Animate and draw sperm cells ---
  for (let cell of spermCells) {
    // Pull toward current mesh point (elastic, but loose)
    let p = mesh[cell.meshIdx.y][cell.meshIdx.x];
    let fx = (p.x - cell.x) * 0.01;
    let fy = (p.y - cell.y) * 0.01;

    // Add organic drift (Perlin noise)
    fx += (noise(cell.x * 0.01, frameCount * 0.01) - 0.5) * 0.5;
    fy += (noise(cell.y * 0.01, frameCount * 0.01) - 0.5) * 0.5;

    // Add velocity and damping
    cell.vx = (cell.vx + fx) * 0.96;
    cell.vy = (cell.vy + fy) * 0.96;
    cell.x += cell.vx;
    cell.y += cell.vy;

    // Draw the asset (centered, scaled to max 64px)
    imageMode(CENTER);
    let maxSize = 64;
    let scale = min(maxSize / max(cell.img.width, cell.img.height), 1);
    image(cell.img, cell.x, cell.y, cell.img.width * scale, cell.img.height * scale);
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