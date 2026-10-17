import os
import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

app = FastAPI(title="TikTok Video Compressor")

TEMP_DIR = "/tmp/tiktok_proc"
os.makedirs(TEMP_DIR, exist_ok=True)


def cleanup_files(*file_paths):
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@app.get("/", response_class=HTMLResponse)
async def render_home():
    return """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>TikTok Video Optimizer</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #090d16 100%);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                -webkit-tap-highlight-color: transparent;
            }
            .glass-card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(24px);
                -webkit-backdrop-filter: blur(24px);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            .glass-input {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .glass-input:focus {
                border-color: rgba(99, 102, 241, 0.5);
                background: rgba(255, 255, 255, 0.1);
            }
            .ios-btn {
                background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                box-shadow: 0 8px 20px -4px rgba(99, 102, 241, 0.4);
            }
            .ios-btn:active {
                transform: scale(0.98);
            }
        </style>
    </head>
    <body class="text-slate-100 min-h-screen flex flex-col justify-between p-4 sm:p-6 antialiased">
        
        <main class="w-full max-w-md mx-auto my-auto py-6">
            <div class="glass-card rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
                
                <!-- Ambient Glow -->
                <div class="absolute -top-12 -right-12 w-32 h-32 bg-indigo-500/20 rounded-full blur-2xl pointer-events-none"></div>
                <div class="absolute -bottom-12 -left-12 w-32 h-32 bg-purple-500/20 rounded-full blur-2xl pointer-events-none"></div>

                <!-- Header -->
                <div class="text-center mb-8 relative z-10">
                    <div class="w-12 h-12 bg-indigo-500/20 border border-indigo-400/30 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-inner">
                        <i class="fa-solid fa-wand-magic-sparkles text-indigo-400 text-xl"></i>
                    </div>
                    <h1 class="text-xl font-semibold tracking-tight text-white">TikTok Video Optimizer</h1>
                    <p class="text-xs text-slate-400 mt-1">Render ulang 1080x1920 & sharpening via FFmpeg</p>
                </div>

                <!-- Upload Form -->
                <form id="uploadForm" onsubmit="handleUpload(event)" class="space-y-5 relative z-10">
                    
                    <!-- File Dropzone -->
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-2 uppercase tracking-wider">Berkas Video</label>
                        <div id="dropZone" onclick="document.getElementById('videoFile').click()" 
                            class="glass-input border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all hover:bg-white/10 flex flex-col items-center justify-center group">
                            <i class="fa-solid fa-cloud-arrow-up text-3xl text-slate-400 group-hover:text-indigo-400 transition-colors mb-2"></i>
                            <span id="fileName" class="text-xs text-slate-300 font-medium truncate max-w-[200px]">Pilih atau seret MP4 / MOV</span>
                            <span class="text-[10px] text-slate-500 mt-1">Maksimal 200MB</span>
                            <input type="file" id="videoFile" accept="video/mp4,video/quicktime,video/*" required class="hidden" onchange="updateFileName(this)">
                        </div>
                    </div>

                    <!-- Target FPS -->
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-2 uppercase tracking-wider">Framerate (FPS)</label>
                        <div class="grid grid-cols-2 gap-3">
                            <label class="cursor-pointer">
                                <input type="radio" name="fps" value="30" checked class="peer hidden">
                                <div class="glass-input text-center py-3 rounded-xl text-xs font-medium text-slate-300 peer-checked:bg-indigo-600 peer-checked:text-white peer-checked:border-indigo-500 transition-all">
                                    30 FPS (Standar)
                                </div>
                            </label>
                            <label class="cursor-pointer">
                                <input type="radio" name="fps" value="60" class="peer hidden">
                                <div class="glass-input text-center py-3 rounded-xl text-xs font-medium text-slate-300 peer-checked:bg-indigo-600 peer-checked:text-white peer-checked:border-indigo-500 transition-all">
                                    60 FPS (Smooth)
                                </div>
                            </label>
                        </div>
                    </div>

                    <button type="submit" id="submitBtn" class="ios-btn w-full text-white font-medium py-3.5 px-4 rounded-xl text-sm transition-all flex items-center justify-center gap-2 cursor-pointer mt-2">
                        <span>Proses Video</span>
                        <i class="fa-solid fa-arrow-right text-xs"></i>
                    </button>
                </form>

                <!-- Processing / Loading State -->
                <div id="loadingIndicator" class="hidden text-center py-8 space-y-4 relative z-10">
                    <div class="relative w-16 h-16 mx-auto flex items-center justify-center">
                        <div class="absolute inset-0 border-4 border-indigo-500/20 rounded-full"></div>
                        <div class="absolute inset-0 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                        <i class="fa-solid fa-gear text-indigo-400 text-lg animate-pulse"></i>
                    </div>
                    <div class="space-y-1">
                        <p class="text-sm font-semibold text-white">Memproses Video...</p>
                        <p id="statusText" class="text-xs text-slate-400">Mengunggah ke server...</p>
                    </div>
                    <div class="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden border border-white/5">
                        <div id="progressBar" class="bg-indigo-500 h-full w-0 transition-all duration-300"></div>
                    </div>
                </div>

                <!-- Result State -->
                <div id="resultContainer" class="hidden text-center py-4 space-y-4 relative z-10">
                    <div class="w-12 h-12 bg-emerald-500/20 border border-emerald-500/30 rounded-full flex items-center justify-center mx-auto text-emerald-400 text-xl">
                        <i class="fa-solid fa-check"></i>
                    </div>
                    <div>
                        <h3 class="text-base font-semibold text-white">Video Selesai Dirender</h3>
                        <p class="text-xs text-slate-400 mt-0.5">Format 1080x1920 siap diunggah ke TikTok.</p>
                    </div>
                    
                    <a id="downloadLink" href="#" class="ios-btn block w-full text-white font-medium py-3.5 px-4 rounded-xl text-sm transition-all text-center">
                        <i class="fa-solid fa-download mr-2"></i>Unduh Hasil Video
                    </a>
                    
                    <button onclick="resetForm()" class="text-xs text-slate-400 hover:text-white transition-colors cursor-pointer pt-2 block mx-auto">
                        Kompres video lain
                    </button>
                </div>

            </div>
        </main>

        <footer class="text-center py-4 text-[11px] text-slate-500 relative z-10">
            TikTok Optimizer &bull; High Quality FFmpeg Pipeline
        </footer>

        <script>
            function updateFileName(input) {
                const fileName = document.getElementById('fileName');
                if (input.files.length > 0) {
                    fileName.innerText = input.files[0].name;
                    fileName.classList.add('text-indigo-300');
                }
            }

            async function handleUpload(event) {
                event.preventDefault();
                
                const fileInput = document.getElementById('videoFile');
                const fpsValue = document.querySelector('input[name="fps"]:checked').value;
                
                if (!fileInput.files.length) return;

                const form = document.getElementById('uploadForm');
                const loading = document.getElementById('loadingIndicator');
                const statusText = document.getElementById('statusText');
                const progressBar = document.getElementById('progressBar');

                form.classList.add('hidden');
                loading.classList.remove('hidden');

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('fps', fpsValue);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/process', true);

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        progressBar.style.width = percent + '%';
                        if (percent < 100) {
                            statusText.innerText = `Mengunggah: ${percent}%`;
                        } else {
                            statusText.innerText = 'Server sedang memproses & mengompres video...';
                            progressBar.classList.add('animate-pulse');
                        }
                    }
                };

                xhr.onload = function() {
                    if (xhr.status === 200) {
                        const data = JSON.parse(xhr.responseText);
                        loading.classList.add('hidden');
                        document.getElementById('resultContainer').classList.remove('hidden');
                        document.getElementById('downloadLink').href = `/download/${data.filename}`;
                    } else {
                        alert('Gagal memproses video.');
                        resetForm();
                    }
                };

                xhr.onerror = function() {
                    alert('Koneksi terputus.');
                    resetForm();
                };

                xhr.send(formData);
            }

            function resetForm() {
                document.getElementById('uploadForm').reset();
                document.getElementById('fileName').innerText = 'Pilih atau seret MP4 / MOV';
                document.getElementById('fileName').classList.remove('text-indigo-300');
                document.getElementById('progressBar').style.width = '0%';
                document.getElementById('uploadForm').classList.remove('hidden');
                document.getElementById('resultContainer').classList.add('hidden');
                document.getElementById('loadingIndicator').classList.add('hidden');
            }
        </script>
    </body>
    </html>
    """


@app.post("/process")
async def process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fps: int = Form(30)
):
    req_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(TEMP_DIR, f"input_{req_id}.mp4")
    output_filename = f"tiktok_optimal_{req_id}.mp4"
    output_path = os.path.join(TEMP_DIR, output_filename)

    try:
        with open(input_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan file: {str(e)}")

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-maxrate", "18M",
        "-bufsize", "36M",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-g", str(fps),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,unsharp=5:5:0.8:5:5:0.0",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]

    # Run FFmpeg asynchronously without blocking event loop
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await proc.wait()

    background_tasks.add_task(cleanup_files, input_path)

    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail="FFmpeg gagal memproses video.")

    return {"filename": output_filename}


@app.get("/download/{filename}")
async def download_file(background_tasks: BackgroundTasks, filename: str):
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Berkas tidak ditemukan atau sudah kadaluarsa.")
    
    background_tasks.add_task(cleanup_files, file_path)

    return FileResponse(
        path=file_path,
        filename="video_tiktok_optimal.mp4",
        media_type="video/mp4"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
