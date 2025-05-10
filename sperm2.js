let cols = 20, rows_ = 14;
let mesh = [];
let nodes = [];
let keyToNode = {};
let assets = [];
let assetCount = 333; // Set to your number of PNGs
let spermCells = [];

function preload() {
    for (let i = 1; i <= assetCount; i++) {
      assets.push(loadImage(
        'algo/line_' + i + '.PNG',
        () => {}, // success callback
        () => { console.error('Failed to load: algo/line_' + i + '.png'); }
      ));
    }
}

function windowResized() {
    resizeCanvas(windowWidth, windowHeight);
}

function setup() {
  createCanvas(windowWidth, windowHeight, WEBGL);

  let marginX = 80;
  let marginY = 80;

  // 1. Create mesh grid (invisible substrate) -- now fills the viewport
  mesh = [];
  for (let y = 0; y < rows_; y++) {
    let meshRow = [];
    for (let x = 0; x < cols; x++) {
      // Map mesh to fill most of the window, with a margin
      let px = map(x, 0, cols - 1, -width / 2 + marginX, width / 2 - marginX);
      let py = map(y, 0, rows_ - 1, -height / 2 + marginY, height / 2 - marginY);
      meshRow.push({
        x: px,
        y: py,
        vx: 0, vy: 0,
        rest_x: px,
        rest_y: py
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
    let y = map(row, 0, totalRows - 1, -height / 2 + marginY, height / 2 - marginY);
    for (let col = 0; col < keys.length; col++) {
      let x = map(col, 0, keys.length - 1, -width / 2 + marginX, width / 2 - marginX);
      let key = keys[col];
      let node = { x, y, force: 0 };
      nodes.push(node);
      keyToNode[key] = nodes.length - 1;
    }
  }

  // 3. Create sperm cells, scattered randomly
  spermCells = [];
  let desiredAssetCount = 800; // set your desired number of sperm cells
  let minSpacing = 50;         // Minimum spacing between pieces

  for (let i = 0; i < desiredAssetCount; i++) {
  let candidate;
  let attempts = 0;
  
  // Try at most 30 times to find a candidate with enough spacing
  while (attempts < 30) {
    let x = random(-width / 2 + marginX, width / 2 - marginX);
    let y = random(-height / 2 + marginY, height / 2 - marginY);
    candidate = { x, y };
    let conflict = false;
    for (let cell of spermCells) {
      if (dist(cell.x, cell.y, candidate.x, candidate.y) < minSpacing) {
        conflict = true;
        break;
      }
    }
    if (!conflict) {
      break;
    }
    attempts++;
  }
  spermCells.push({
    x: candidate.x,
    y: candidate.y,
    vx: random(-1, 1),
    vy: random(-1, 1),
    img: assets[i % assets.length], // Cycle through assets if needed
    scale: random(0.3, 0.5),          // Smaller asset scale
    angle: random(TWO_PI),
    angleSpeed: random(-0.02, 0.02)
    });
  }
  
}

let lastShuffle = 0;
let shuffleInterval = 111; // milliseconds (0.5 seconds)

function draw() {
  background(255);
  orbitControl();

  // Shuffle a few sperm cell images at a set interval
  if (millis() - lastShuffle > shuffleInterval) {
    let swapsPerInterval = 36; // Number of swaps per interval
    for (let n = 0; n < swapsPerInterval; n++) {
      let i = floor(random(spermCells.length));
      let j = floor(random(spermCells.length));
      // Swap the img property only
      let temp = spermCells[i].img;
      spermCells[i].img = spermCells[j].img;
      spermCells[j].img = temp;
    }
    lastShuffle = millis();
  }

  // --- Mesh physics (invisible) ---
  for (let y = 0; y < rows_; y++) {
    for (let x = 0; x < cols; x++) {
      let p = mesh[y][x];
      // Spring to rest
      let fx = (p.rest_x - p.x) * 0.04;
      let fy = (p.rest_y - p.y) * 0.04;
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
    // New force calculation from active muscle nodes:
    let fx = 0, fy = 0;
    for (let node of nodes) {
      let d = dist(cell.x, cell.y, node.x, node.y);
      if (node.force > 0 && d < 180) {
          let strength = 3 * node.force * (180 - d) / 180;
          fx += (node.x - cell.x) * strength * 0.005;
          fy += (node.y - cell.y) * strength * 0.005;
      }
    }

    // Add velocity and damping
    cell.vx = (cell.vx + fx) * 0.96;
    cell.vy = (cell.vy + fy) * 0.96;
    cell.x += cell.vx;
    cell.y += cell.vy;

    // Animate rotation
    cell.angle += cell.angleSpeed;

    // Optionally, animate scale for a "breathing" effect:
    let animatedScale = cell.scale + 0.1 * sin(frameCount * 0.03 + cell.x);

    // Draw the asset with rotation and scale
    push();
    translate(cell.x, cell.y);
    rotate(cell.angle);
    imageMode(CENTER);
    let maxSize = 64;
    let scale = min(maxSize / max(cell.img.width, cell.img.height), 1) * animatedScale;
    image(cell.img, 0, 0, cell.img.width * scale, cell.img.height * scale);
    pop();
  }
}

// Helper function: returns true if any node is active
function anyNodeActive() {
    return nodes.some(node => node.force > 0);
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