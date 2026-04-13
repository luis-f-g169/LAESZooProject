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
        ctx.putImageData(frame, 0, 0);
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
