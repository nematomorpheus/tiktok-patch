from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
import subprocess
import uuid
import os

app = FastAPI(title="Kompresor Video TikTok")

TEMP_DIR = "/tmp/tiktok_proc"
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_files(*file_paths):
    """Fungsi latar belakang untuk membersihkan berkas sementara."""
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kompresor Video TikTok</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col justify-between">
        <div class="container mx-auto px-4 py-12 max-w-xl">
            <div class="bg-slate-800 border border-slate-700 rounded-2xl shadow-xl p-8">
                
                <!-- Header -->
                <div class="text-center mb-8">
                    <h1 class="text-2xl font-bold tracking-tight text-white mb-2">Kompresor Video TikTok</h1>
                    <p class="text-sm text-slate-400">Optimalkan kualitas video Anda langsung melalui server.</p>
                </div>
                
                <!-- Form Upload -->
                <form id="uploadForm" onsubmit="handleUpload(event)" class="space-y-6">
                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-2">Pilih Berkas Video (MP4 / MOV)</label>
                        <input type="file" id="videoFile" accept="video/mp4,video/quicktime,video/*" required
                            class="w-full text-sm text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-emerald-600 file:text-white hover:file:bg-emerald-700 file:cursor-pointer bg-slate-900/50 border border-slate-700 rounded-xl cursor-pointer">
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-2">Pengaturan Frame (FPS)</label>
                        <select id="videoFps" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-emerald-500">
                            <option value="30">30 FPS (Stabil & Optimal)</option>
                            <option value="60">60 FPS (Halus & Dinamis)</option>
                        </select>
                    </div>

                    <button type="submit" id="submitBtn" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-3 px-4 rounded-xl transition duration-200 shadow-lg shadow-emerald-600/20 cursor-pointer">
                        Proses Video
                    </button>
                </form>

                <!-- Loading State -->
                <div id="loadingIndicator" class="hidden text-center py-6 space-y-3">
                    <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-emerald-500 border-t-transparent"></div>
                    <p class="text-sm text-slate-200 font-semibold">Server sedang merender video...</p>
                    <p class="text-xs text-slate-400">Proses sedang berjalan di latar belakang. Mohon menunggu sebentar.</p>
                </div>

                <!-- Success Result State (Tombol Download) -->
                <div id="resultContainer" class="hidden text-center py-4 space-y-4">
                    <div class="bg-emerald-950/50 border border-emerald-500/30 rounded-xl p-4 text-emerald-400 text-sm font-medium">
                        Berhasil! Video Anda telah selesai dirender.
                    </div>
                    <a id="downloadLink" href="#" class="block w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-4 rounded-xl transition duration-200 shadow-lg shadow-indigo-600/20 text-center">
                        Unduh Video
                    </a>
                    <button onclick="resetForm()" class="text-xs text-slate-400 hover:text-white underline cursor-pointer pt-2">
                        Kompres video lainnya
                    </button>
                </div>

            </div>
        </div>

        <footer class="text-center py-6 text-xs text-slate-500 border-t border-slate-800">
            Sistem Pengolahan Video &copy; 2026
        </footer>

        <script>
            async function handleUpload(event) {
                event.preventDefault();
                
                const fileInput = document.getElementById('videoFile');
                const fpsSelect = document.getElementById('videoFps');
                
                if (fileInput.files.length === 0) return;

                document.getElementById('uploadForm').style.display = 'none';
                document.getElementById('loadingIndicator').style.display = 'block';

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('fps', fpsSelect.value);

                try {
                    const response = await fetch('/process', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) throw new Error('Gagal memproses video di server.');

                    const data = await response.json();

                    document.getElementById('loadingIndicator').style.display = 'none';
                    document.getElementById('resultContainer').style.display = 'block';
                    
                    const downloadBtn = document.getElementById('downloadLink');
                    downloadBtn.href = `/download/${data.filename}`;
                } catch (error) {
                    alert(error.message);
                    resetForm();
                }
            }

            function resetForm() {
                document.getElementById('uploadForm').reset();
                document.getElementById('uploadForm').style.display = 'block';
                document.getElementById('resultContainer').style.display = 'none';
                document.getElementById('loadingIndicator').style.display = 'none';
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
    log_path = os.path.join(TEMP_DIR, f"log_{req_id}.txt")

    with open(input_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

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

    with open(log_path, "w") as log_file:
        subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT)

    background_tasks.add_task(cleanup_files, input_path, log_path)

    return {"filename": output_filename}

@app.get("/download/{filename}")
async def download_file(background_tasks: BackgroundTasks, filename: str):
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "Berkas tidak ditemukan atau sudah kadaluarsa."}
    
    background_tasks.add_task(cleanup_files, file_path)

    return FileResponse(
        path=file_path,
        filename="video_tiktok.mp4",
        media_type="video/mp4"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
