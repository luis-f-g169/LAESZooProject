from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


HTML = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Animal Vision Camera</title>
  <style>
    body {
      font-family: sans-serif;
      margin: 0;
      padding: 16px;
      background: #111;
      color: white;
    }
    #video, #canvas {
      width: 100%;
      max-width: 520px;
      border-radius: 12px;
      display: block;
      margin-bottom: 12px;
    }
    button {
      font-size: 16px;
      padding: 12px 16px;
      margin: 8px 8px 8px 0;
    }
    #result {
      margin-top: 12px;
      font-size: 18px;
    }
    #status {
      opacity: 0.8;
      margin-bottom: 8px;
    }
  </style>
</head>
<body>
  <h2>Live Camera → Animal Vision Filter</h2>
  <div id="status">Not connected</div>
  <video id="video" autoplay playsinline muted style="display:none;"></video>
  <canvas id="canvas"></canvas>

  <div>
    <button id="startBtn">Start Camera</button>
  </div>

  // You can customize these filters to better match the vision of each animal type

  <div style="margin-top: 16px;">
  <label for="visionSelect">Choose Animal Vision:</label>
  <select id="visionSelect" style="font-size:16px; padding:10px; margin-left:8px;">
    <option value="normal">Normal</option>
    <option value="reptile">Alligator / Reptile</option>
    <option value="bird">Bird</option>
    <option value="mammal">Mammal</option>
    <option value="primate">Primate</option>
    <option value="bigcat">Big Cat</option>
    <option value="canid">Canid / Dog-like</option>
    <option value="fiji">Fiji Banded Iguana</option>
  </select>
</div>

  <div id="result">Selected Vision: Normal</div>

  <script>

    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const statusEl = document.getElementById("status");
    const resultEl = document.getElementById("result");

    const visionSelect = document.getElementById("visionSelect");

    let stream = null;
    let currentFilter = "normal";

    // Offscreen canvases reused each frame for the Fiji vignette-blur effect
    let fijiBlurCanvas = null;
    let fijiMaskCanvas = null;

    async function startCamera() {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          statusEl.textContent = "Camera error: HTTPS required for camera access";
          return false;
        }

        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 640 },
            height: { ideal: 480 }
          },
          audio: false
        });

        video.srcObject = stream;
        await video.play();
        statusEl.textContent = "Camera ready";
        return true;
      } catch (err) {
        statusEl.textContent = "Camera error: " + err.message;
        return false;
      }
    }

  visionSelect.onchange = () => {
    currentFilter = visionSelect.value;
    resultEl.textContent = `Selected Vision: ${visionSelect.options[visionSelect.selectedIndex].text}`;
  };

// ── HSL helpers ──────────────────────────────────────────────────────────────
function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h;
  if      (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else                h = ((r - g) / d + 4) / 6;
  return [h, s, l];
}

function hslToRgb(h, s, l) {
  if (s === 0) { const v = Math.round(l * 255); return [v, v, v]; }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  function hue2rgb(t) {
    if (t < 0) t += 1; if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 0.5)   return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  }
  return [
    Math.round(hue2rgb(h + 1 / 3) * 255),
    Math.round(hue2rgb(h)         * 255),
    Math.round(hue2rgb(h - 1 / 3) * 255)
  ];
}

// ── Barrel distortion (fisheye) pixel remap ───────────────────────────────────
// k > 0 → barrel (fisheye / wide-angle look); corresponds to Bulge –60%
function applyBarrelDistortion(imageData, k) {
  const w = imageData.width, h = imageData.height;
  const src = new Uint8ClampedArray(imageData.data);
  const dst = imageData.data;
  const cx = w / 2, cy = h / 2;
  for (let py = 0; py < h; py++) {
    for (let px = 0; px < w; px++) {
      const xn = (px - cx) / cx;
      const yn = (py - cy) / cy;
      const rr = Math.sqrt(xn * xn + yn * yn);
      const di = (py * w + px) * 4;
      if (rr < 0.0001) continue;              // centre pixel unchanged
      const rSrc = rr / (1 + k * rr * rr);   // inverse barrel mapping
      const sx = Math.round(xn / rr * rSrc * cx + cx);
      const sy = Math.round(yn / rr * rSrc * cy + cy);
      if (sx >= 0 && sx < w && sy >= 0 && sy < h) {
        const si = (sy * w + sx) * 4;
        dst[di]     = src[si];
        dst[di + 1] = src[si + 1];
        dst[di + 2] = src[si + 2];
      } else {
        dst[di] = dst[di + 1] = dst[di + 2] = 0;
      }
    }
  }
  return imageData;
}

function applyFilter(imageData, filterName) {
  const data = imageData.data;

  for (let i = 0; i < data.length; i += 4) {
    let r = data[i];
    let g = data[i + 1];
    let b = data[i + 2];

    if (filterName === "bigcat") {
      // lower saturation, slightly brighter shadows
      const gray = 0.3 * r + 0.59 * g + 0.11 * b;
      data[i]     = Math.min(255, 0.55 * gray + 0.45 * r + 8);
      data[i + 1] = Math.min(255, 0.55 * gray + 0.45 * g + 8);
      data[i + 2] = Math.min(255, 0.55 * gray + 0.45 * b + 8);

    } else if (filterName === "canid") {
      // dog-like yellow/blue approximation
      const newR = 0.45 * r + 0.35 * g;
      const newG = 0.55 * g + 0.25 * b;
      const newB = 0.95 * b + 0.10 * g;
      data[i]     = Math.min(255, newR);
      data[i + 1] = Math.min(255, newG);
      data[i + 2] = Math.min(255, newB);

    } else if (filterName === "bird") {
      // more vivid / higher contrast artistic look
      data[i]     = Math.min(255, 1.15 * r);
      data[i + 1] = Math.min(255, 1.15 * g);
      data[i + 2] = Math.min(255, 1.2 * b);

    } else if (filterName === "reptile") {
      // heatmap-ish artistic reptile view
      const intensity = (r + g + b) / 3;
      data[i]     = intensity > 170 ? 255 : intensity;
      data[i + 1] = intensity > 100 ? 140 : 20;
      data[i + 2] = intensity < 90 ? 255 : 0;

    } else if (filterName === "primate") {
      // close to normal human-like color
      data[i]     = r;
      data[i + 1] = g;
      data[i + 2] = b;

    } else if (filterName === "mammal") {
      // mild desaturation
      const gray = 0.3 * r + 0.59 * g + 0.11 * b;
      data[i]     = 0.75 * r + 0.25 * gray;
      data[i + 1] = 0.75 * g + 0.25 * gray;
      data[i + 2] = 0.75 * b + 0.25 * gray;

    } else if (filterName === "fiji") {
      // === Fiji Banded Iguana Vision ===
      // Hue +20°, Saturation +20, Lightness +10, Shadows –15, Contrast –20
      // Fisheye barrel distortion + vignette blur handled in renderLoop

      // HSL adjustments
      let [hF, sF, lF] = rgbToHsl(r, g, b);
      hF = (hF + 20 / 360) % 1;       // Hue +20°
      sF = Math.min(1, sF + 0.20);     // Saturation +20
      lF = Math.min(1, lF + 0.10);     // Lightness +10
      let [rF, gF, bF] = hslToRgb(hF, sF, lF);

      // Shadows –15: darken pixels below mid-luminance
      const lumF = 0.299 * rF + 0.587 * gF + 0.114 * bF;
      const shadowAdj = -15 * Math.max(0, 1 - lumF / 128);
      rF = Math.max(0, rF + shadowAdj);
      gF = Math.max(0, gF + shadowAdj);
      bF = Math.max(0, bF + shadowAdj);

      // Contrast –20: pull all tones toward midgray (128)
      rF = 128 + (rF - 128) * 0.80;
      gF = 128 + (gF - 128) * 0.80;
      bF = 128 + (bF - 128) * 0.80;

      // Exposure –20: uniform darkening across all tones
      rF -= 20;
      gF -= 20;
      bF -= 20;

      data[i]     = Math.min(255, Math.max(0, rF));
      data[i + 1] = Math.min(255, Math.max(0, gF));
      data[i + 2] = Math.min(255, Math.max(0, bF));
    }
  }

  return imageData;
}

    function renderLoop() {
      if (video.videoWidth > 0) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        let frame = ctx.getImageData(0, 0, canvas.width, canvas.height);
        frame = applyFilter(frame, currentFilter);

        if (currentFilter === "fiji") {
          // Fisheye barrel distortion
          frame = applyBarrelDistortion(frame, 0.2);
        }

        ctx.putImageData(frame, 0, 0);

        if (currentFilter === "fiji") {
          const w = canvas.width;
          const h = canvas.height;

          // ── Vignette blur: sharp centre, blurred edges ──────────────────────
          // Lazily build (or rebuild on resize) the two helper canvases
          if (!fijiBlurCanvas || fijiBlurCanvas.width !== w || fijiBlurCanvas.height !== h) {
            fijiBlurCanvas = document.createElement("canvas");
            fijiBlurCanvas.width = w;
            fijiBlurCanvas.height = h;

            fijiMaskCanvas = document.createElement("canvas");
            fijiMaskCanvas.width = w;
            fijiMaskCanvas.height = h;

            // Static radial mask: transparent centre → opaque at edges
            const mCtx = fijiMaskCanvas.getContext("2d");
            const radMask = mCtx.createRadialGradient(w / 2, h / 2, h * 0.25, w / 2, h / 2, h * 0.60);
            radMask.addColorStop(0, "rgba(0,0,0,0)");
            radMask.addColorStop(1, "rgba(0,0,0,1)");
            mCtx.fillStyle = radMask;
            mCtx.fillRect(0, 0, w, h);
          }

          // Draw blurred copy of current frame onto fijiBlurCanvas
          const bCtx = fijiBlurCanvas.getContext("2d");
          bCtx.clearRect(0, 0, w, h);
          bCtx.filter = "blur(7px)";
          bCtx.drawImage(canvas, 0, 0);
          bCtx.filter = "none";

          // Mask blurred copy so only the edge ring shows through
          bCtx.globalCompositeOperation = "destination-in";
          bCtx.drawImage(fijiMaskCanvas, 0, 0);
          bCtx.globalCompositeOperation = "source-over";

          // Composite the masked blur over the sharp canvas
          ctx.drawImage(fijiBlurCanvas, 0, 0);
        }
      }

      requestAnimationFrame(renderLoop);
    }

    function sendFrame() {
      if (!ws || ws.readyState !== WebSocket.OPEN || !video.videoWidth) return;

      const tempCanvas = document.createElement("canvas");
      const tempCtx = tempCanvas.getContext("2d");

      const targetWidth = 224;
      const scale = targetWidth / video.videoWidth;
      const targetHeight = Math.round(video.videoHeight * scale);

      tempCanvas.width = targetWidth;
      tempCanvas.height = targetHeight;
      tempCtx.drawImage(video, 0, 0, targetWidth, targetHeight);

      const dataUrl = tempCanvas.toDataURL("image/jpeg", 0.6);
      ws.send(dataUrl);
    }

    document.getElementById("startBtn").onclick = async () => {
      await startCamera();
    };

    renderLoop();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML
