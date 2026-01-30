import redis
import base64
import json
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- FIX: Increase request size limit to 32MB ---
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024 

# --- Redis Configuration ---
REDIS_HOST = 'redis-10394.c62.us-east-1-4.ec2.cloud.redislabs.com'
REDIS_PORT = 10394
REDIS_PASS = 'DcIBnyFIEevH36YawnPButjOrS98WAd7'
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS)

INDEX_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>New Analysis | Cancer Cell Detection</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; }
    .scan-line {
      position: absolute; top: 0; left: 0; width: 100%; height: 4px;
      background: #3b82f6; box-shadow: 0 0 15px #3b82f6;
      animation: scan 2.5s ease-in-out infinite; display: none; z-index: 20;
    }
    @keyframes scan { 0% {top:0%} 50% {top:100%} 100% {top:0%} }
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-50 text-slate-900">
  <nav class="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-40">
    <div class="flex items-center gap-4">
        <div class="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white"><i class="fa-solid fa-dna text-xl"></i></div>
        <div>
            <h1 class="font-bold text-slate-800 leading-tight">Cancer Diagnostic Session</h1>
            <p class="text-xs text-slate-500">Cloud-to-Local Bridge</p>
        </div>
    </div>
  </nav>

  <main class="flex-1 max-w-7xl mx-auto w-full p-4 md:p-8 grid lg:grid-cols-12 gap-8 items-start">
    <div class="lg:col-span-7 space-y-6">
      <div class="bg-white p-6 rounded-3xl shadow-sm border border-slate-200">
          <label class="block text-sm font-bold text-slate-700 mb-3 uppercase tracking-wider">Target Analysis Area</label>
          <select id="cancerType" class="w-full p-4 rounded-xl border border-slate-200 bg-slate-50 font-semibold text-slate-700 outline-none">
              <option value="lung">Lung Cancer</option>
              <option value="breast">Breast Cancer</option>
              <option value="oral">Oral Cancer</option>
              <option value="skin">Skin Cancer</option>
              <option value="brain">Brain Tumor</option>
          </select>
      </div>

      <div id="dropZone" class="bg-white border-2 border-dashed border-slate-300 rounded-3xl h-[450px] flex flex-col items-center justify-center cursor-pointer relative overflow-hidden group shadow-sm">
        <input type="file" id="fileInput" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-30" accept="image/*">
        <div id="uploadPrompt" class="text-center p-6">
          <div class="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4 text-blue-600"><i class="fas fa-microscope text-3xl"></i></div>
          <h3 class="text-xl font-bold text-slate-800 mb-2">Upload Microscopic Slide</h3>
        </div>
        <div id="previewContainer" class="hidden absolute inset-0 bg-slate-900 w-full h-full z-20">
          <img id="imagePreview" class="w-full h-full object-contain opacity-80">
          <div id="scanLine" class="scan-line"></div>
        </div>
      </div>

      <button id="analyzeBtn" class="w-full bg-slate-900 text-white font-bold py-5 rounded-2xl shadow-xl hover:bg-blue-600 transition-all flex items-center justify-center gap-3">
        <span>Initiate Remote Analysis</span> <i class="fa-solid fa-paper-plane"></i>
      </button>
    </div>

    <div class="lg:col-span-5">
      <div class="rounded-3xl p-0 overflow-hidden bg-slate-900 border border-slate-800 h-[600px] flex flex-col shadow-2xl">
        <div class="bg-slate-800/80 border-b border-slate-700 px-5 py-4 text-[11px] font-bold text-slate-400 uppercase">
            <i class="fa-solid fa-terminal mr-2"></i> System Activity Log
        </div>
        <div id="terminal" class="p-5 flex-1 overflow-y-auto text-xs font-mono text-green-400/90 space-y-3">
            <div><span class="text-slate-600">>></span> Initializing bridge...</div>
        </div>
      </div>
    </div>
  </main>

<script>
const terminal = document.getElementById("terminal");
const fileInput = document.getElementById("fileInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const imagePreview = document.getElementById("imagePreview");
const previewContainer = document.getElementById("previewContainer");
const scanLine = document.getElementById("scanLine");

function log(message, color = "text-green-400") {
    const time = new Date().toLocaleTimeString([], { hour12: false });
    const line = document.createElement("div");
    line.innerHTML = `<span class="text-slate-600">${time}</span> <span class="text-blue-500 font-bold">></span> <span class="${color}">${message}</span>`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}

fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            previewContainer.classList.remove('hidden');
            log(`File selected: ${file.name}`);
        };
        reader.readAsDataURL(file);
    }
});

analyzeBtn.addEventListener("click", async () => {
    const file = fileInput.files[0];
    const category = document.getElementById("cancerType").value;
    if (!file) return log("Error: No slide uploaded", "text-red-400");

    scanLine.style.display = 'block';
    log(`Transmitting ${category.toUpperCase()} scan...`, "text-blue-300");

    const reader = new FileReader();
    reader.onload = async function() {
        const base64Data = reader.result.split(',')[1];
        try {
            const response = await fetch("/upload", {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64Data, type: category })
            });
            const result = await response.json();
            if (response.ok) log("Sent to Cloud. Waiting for Local Laptop...", "text-blue-400");
            else log(`Error: ${result.error}`, "text-red-500");
        } catch (e) {
            log("Critical: Cloud connection failed", "text-red-500");
        }
    };
    reader.readAsDataURL(file);
});

setInterval(async () => {
    try {
        const res = await fetch("/get_acks");
        const data = await res.json();
        if(data.acks) {
            data.acks.forEach(msg => {
                log(msg, "text-yellow-400 font-bold");
                scanLine.style.display = 'none';
            });
        }
    } catch (e) {}
}, 2000);
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.get_json(silent=True)
        if not data or 'image' not in data:
            return jsonify({"error": "No image data found in request"}), 400

        package = {"type": data.get('type'), "image_data": data.get('image')}
        r.lpush('image_stream', json.dumps(package))
        return jsonify({"status": "Success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_acks')
def get_acks():
    messages = []
    while True:
        ack = r.rpop('ack_stream')
        if ack: messages.append(ack.decode('utf-8'))
        else: break
    return jsonify({"acks": messages})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)