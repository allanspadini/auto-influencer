from fasthtml.common import *
import shutil
import os
import json
import subprocess
from pathlib import Path
from starlette.staticfiles import StaticFiles
import imageio_ffmpeg
import whisper
import video_processing

# Setup
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

# Custom CSS from the designer
custom_css = """
    /* ---------- Paleta e tokens ---------- */
    :root{
      --bg:#071022;            /* app background */
      --panel:#0c1722;         /* elevated panels */
      --muted:#8b98a6;         /* text secundário */
      --text:#e6eef6;          /* texto principal */
      --accent:#6d5cff;        /* cor de ação */
      --accent-2:#8b63ff;
      --danger:#ff5c6c;
      --glass: rgba(255,255,255,0.03);
      --border: rgba(255,255,255,0.04);
      --radius: 12px;
      --radius-sm:8px;
      --shadow: 0 10px 30px rgba(2,6,23,0.7);
      --gap: 16px;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }

    /* ---------- Reset minimal ---------- */
    *{box-sizing:border-box}
    html,body{
      margin:0;
      background: var(--panel);
      color:var(--text);
      -webkit-font-smoothing:antialiased;
      -moz-osx-font-smoothing:grayscale;
      line-height:1.35;
      padding:32px;
    }
    
    /* Custom scrollers - dark theme */
    body, .panel {
      scrollbar-width: thin;
      scrollbar-color: rgba(255,255,255,0.06) transparent;
    }
    /* Webkit-based */
    ::-webkit-scrollbar{ width:12px; height:12px }
    ::-webkit-scrollbar-track{ background: transparent }
    ::-webkit-scrollbar-thumb{ background: rgba(255,255,255,0.06); border-radius:999px; border:3px solid transparent; background-clip: padding-box }
    ::-webkit-scrollbar-corner{ background: transparent }

    /* ---------- App container ---------- */
    .app-container{
      width: 100%;
      max-width: 100%;
      margin:0;
      display:flex;
      flex-direction:column;
      gap:20px;
      padding:24px;
      border-radius:16px;
      background:var(--panel);
      min-height: calc(100vh - 64px); /* Full height minus body padding */
    }
    
    /* ---------- Header ---------- */
    header.top{
      position: relative;
      display:flex;
      align-items:center;
      gap:20px;
    }

    .brand{
      display:flex;gap:14px;align-items:center;
    }
    .brand .logo{
      width:48px;height:48px;border-radius:10px;
      background:linear-gradient(135deg,var(--accent),var(--accent-2));
      display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:16px;box-shadow:0 8px 30px rgba(108,92,255,0.18);
    }
    .brand .title{
      font-size:24px;
      font-weight:800;
      letter-spacing:0.2px;
    }
    .brand .subtitle{
      font-size:14px;
      color:var(--muted);
      margin-top:4px;
      max-width:520px;
    }

    .actions{
      position:absolute;
      top:0;
      right:0;
      display:flex;
      gap:10px;
      align-items:center;
    }
    .btn{padding:10px 14px;border-radius:999px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;font-weight:600; text-decoration: none; display: inline-flex; justify-content: center; align-items: center;}
    .btn.ghost{background:var(--glass)}
    .btn.primary{background:linear-gradient(90deg,var(--accent),var(--accent-2));border:none;box-shadow:0 8px 28px rgba(109,92,255,0.18); color: white;}
    .btn.warn{background:transparent;border:1px solid rgba(255,92,108,0.14);color:var(--danger)}
    .btn.secondary{background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); color:var(--text); transition: background 0.2s;}
    .btn.secondary:hover{background:rgba(255,255,255,0.1);}
    
    /* Fixed width for some buttons to match design blocks */
    .action-block button { width: 100%; }

    /* ---------- Grid principal ---------- */
    .main{
      display:grid;
      grid-template-columns:320px 1fr 360px;
      gap:var(--gap);
      align-items:stretch;
      flex: 1; /* Grow to fill container */
    }
    
    /* ---------- Painel (comum) ---------- */
    .panel{
      background:var(--panel);
      border-radius:var(--radius);
      padding:14px; /* reduced padding */
      border:1px solid var(--border);
      box-shadow:var(--shadow);
      min-height:auto;
      height:auto;
      display:flex;
      flex-direction:column;
    }
    
    .panel h3{margin:0 0 6px 0;font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em}
    .panel .title{font-size:15px;margin-bottom:8px;color:var(--text);font-weight:600}

    /* ---------- Controles (coluna esquerda) ---------- */
    .controls{display:flex;flex-direction:column;gap:14px}

    .field{background:linear-gradient(180deg,rgba(255,255,255,0.01),transparent);padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.02)}
    .row{display:flex;gap:10px}
    label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}
    input[type=number], .input{width:100%;padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);background:transparent;color:var(--text)}

    .muted{color:var(--muted);font-size:13px}

    /* botão de ação grande */
    .action-block{display:flex;flex-direction:column;gap:10px}
    .big{padding:12px;border-radius:10px;border:none;background:linear-gradient(90deg,var(--accent),var(--accent-2));color:white;font-weight:700; cursor: pointer; width: 100%;}
    
    /* slider custom simples */
    .slider-wrap{display:flex;align-items:center;gap:12px}
    input[type=range]{-webkit-appearance:none;height:8px;border-radius:999px;background:linear-gradient(90deg, rgba(109,92,255,0.25), rgba(139,99,255,0.15));outline:none; width: 100%;}
    input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.6); cursor: pointer;}

    .small-pill{padding:6px 10px;border-radius:999px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.02);font-size:13px; white-space: nowrap;}

    /* ---------- Preview (centro) ---------- */
    .preview{display:flex;flex-direction:column;gap:12px;flex:1}
    .video-area{
      display:flex;
      align-items:center;
      justify-content:center;
      padding:12px;
      border-radius:12px;
      background:linear-gradient(180deg, rgba(255,255,255,0.01), transparent);
      min-height:260px; /* reduced height */
    }

    .player {
      width:100%;
      /* height:520px;  let video define height or max it */
      max-height: 40vh; /* Changed from 80vh as per user request */
      border-radius:16px;
      overflow:hidden;
      background:#000;
      border:1px solid rgba(255,255,255,0.03);
      display:flex;
      align-items:center;
      justify-content: center;
      position:relative;
      flex-direction: column;
    }
    
    .player video {width:100%;height:100%;object-fit:contain}
    .player .badge{position:absolute;left:12px;top:12px;background:rgba(0,0,0,0.5);padding:6px 10px;border-radius:8px;font-size:12px;color:var(--muted)}

    .timeline{height:6px;background:linear-gradient(90deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));border-radius:6px;position:relative;overflow:hidden}
    .timeline .fill{height:100%;width:0%;background:linear-gradient(90deg,#3ef 10%,#8b63ff)}

    .meta-row{display:flex;justify-content:space-between;align-items:center}

    /* waveform placeholder */
    .wave{
      height:120px; 
      border-radius:10px;
      background:linear-gradient(90deg, rgba(8, 14, 28, 0.6), rgba(10, 20, 40, 0.6));
      border: 1px solid var(--border);
      display:block; /* Changed from flex to block for WaveSurfer compatibility */
      padding:10px;
      overflow: hidden;
      position: relative;
    }

    /* ---------- Transcrição (direita) ---------- */
    .transcript{display:flex;flex-direction:column;gap:12px}

    .transcript .empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:18px;border-radius:10px;border:1px dashed rgba(255,255,255,0.02);color:var(--muted)}
    .transcript button{width:100%}

    /* ---------- Footer hint ---------- */
    .note{font-size:13px;color:var(--muted)}

    /* ---------- Responsividade ---------- */
    @media (max-width:1100px){
      .main{grid-template-columns:1fr;}
      .player{width:100%;height:auto}
    }
    
    /* HTMX Indicator */
    .htmx-indicator{
        opacity:0;
        transition: opacity 200ms ease-in;
    }
    .htmx-request .htmx-indicator{
        opacity:1
    }
    .htmx-request.htmx-indicator{
        opacity:1
    }

    #subtitle-overlay {
        position: absolute;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        text-align: center;
        color: white;
        font-size: 20px;
        font-weight: 600;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        pointer-events: none;
        z-index: 10;
        display: none;
        background: rgba(0,0,0,0.4);
        padding: 4px 10px;
        border-radius: 4px;
    }
"""

hdrs = (
    Style(custom_css),
)

app, rt = fast_app(hdrs=hdrs, pico=False)

def Layout(content):
    return (
        Title("Auto Influencer — Editor (Dark UI)"),
        Body(
            Div(
                # Header
                Header(
                    Div(
                        Div("AI", cls="logo"),
                        Div(
                            Div("Auto Influencer", cls="title"),
                            Div("AI-powered video editor that automatically removes silences, adjusts audio levels, and prepares your content for fast publishing.", cls="subtitle"),
                        ),
                        cls="brand"
                    ),
                    Div(
                        A("New Project", href="/", cls="btn ghost"),
                        Form(
                            Button("Clear Project", cls="btn warn", style="cursor: pointer;"),
                            action="/clean", method="post",
                            style="display: inline;"
                        ),
                        cls="actions"
                    ),
                    cls="top"
                ),
                
                # Main Grid
                Main(
                   content,
                   cls="main"
                ),
                
                cls="app-container"
            )
        )
    )

@rt('/')
def get():
    return Layout(
        Div(
             # Centered upload for home
             Div(
                H3("Upload Video", style="margin-top:0; color:var(--text); font-weight:700; font-size: 24px;"),
                P("Select a video file to begin editing.", cls="muted", style="margin-bottom: 20px;"),
                Form(
                    Input(type="file", name="video", accept="video/*", required=True, cls="input", style="margin-bottom: 20px; border: 1px solid var(--border);"),
                    Button("Upload", cls="big", style="width: 100%;"),
                    action="/upload", method="post", enctype="multipart/form-data"
                ),
                cls="panel", 
                style="max-width: 500px; margin: 100px auto; align-items: center; text-align: center;"
             ),
             style="grid-column: 1 / -1; display: flex;"
        )
    )


# Static mounting for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def extract_audio(video_path: Path):
    audio_path = video_path.with_suffix(".mp3")

    if not audio_path.exists():
        # FFmpeg command to extract audio
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(video_path),
            "-vn", "-acodec", "libmp3lame", str(audio_path)
        ]
        subprocess.run(cmd, check=True)
    return audio_path.name

@rt('/upload')
async def post(video: UploadFile):
    if not video.filename:
        return Redirect('/')
    
    file_path = upload_dir / video.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    # Extract audio immediately
    try:
        extract_audio(file_path)
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return Titled("Error", Div(f"Failed to process video: {e}"))
        
    return Redirect(f'/editor?filename={video.filename}')


def perform_cut(video_path: Path, start: float, end: float):
    # Create new filename
    original_name = video_path.stem
    extension = video_path.suffix
    new_filename = f"{original_name}_removed_{int(start)}_{int(end)}{extension}"
    output_path = video_path.parent / new_filename
    
    # Use video_processing logic
    video_processing.remove_segment(str(video_path), str(output_path), start, end)
    
    return new_filename

@rt('/cut')
async def post(filename: str, start: float, end: float):
    video_path = upload_dir / filename
    if not video_path.exists():
        return Titled("Error", Div("Video file not found"))
        
    try:
        new_filename = perform_cut(video_path, start, end)
        extract_audio(upload_dir / new_filename)
        return Redirect(f'/editor?filename={new_filename}&parent={filename}')
    except Exception as e:
        return Titled("Error", Div(f"Failed to cut video: {e}"))

@rt('/autocut_silence')
async def post(filename: str, threshold: float = -30.0, min_duration: float = 0.5):
    video_path = upload_dir / filename
    if not video_path.exists():
        return Titled("Error", Div("Video file not found"))
    
    # Generate new filename
    original_name = video_path.stem
    extension = video_path.suffix
    new_filename = f"{original_name}_autocut_{int(abs(threshold))}_{min_duration}s{extension}"
    output_path = upload_dir / new_filename
    
    try:
        # Run processing
        # Note: This is a blocking operation. For production, use background tasks.
        success = video_processing.remove_silence(str(video_path), str(output_path), threshold_db=threshold, min_duration=min_duration)
        
        if success:
            extract_audio(output_path)
            return Redirect(f'/editor?filename={new_filename}&parent={filename}')
        else:
            return Titled("Error", Div("Failed to auto-cut silence."))
            
    except Exception as e:
        print(f"Auto cut error: {e}")
        return Titled("Error", Div(f"Failed to process video: {e}"))

@rt('/apply_volume')
async def post(filename: str, factor: float):
    video_path = upload_dir / filename
    if not video_path.exists():
        return Titled("Error", Div("Video file not found"))
    
    # Generate new filename
    original_name = video_path.stem
    extension = video_path.suffix
    new_filename = f"{original_name}_vol_{factor}x{extension}"
    output_path = upload_dir / new_filename
    
    try:
        # Run processing
        video_processing.adjust_volume(str(video_path), str(output_path), factor)
        
        extract_audio(output_path)
        return Redirect(f'/editor?filename={new_filename}&parent={filename}')
            
    except Exception as e:
        print(f"Volume adjustment error: {e}")
        return Titled("Error", Div(f"Failed to adjust volume: {e}"))

@rt('/clean')
def post():
    for f in upload_dir.glob("*"):
        try:
            f.unlink()
        except Exception as e:
            print(f"Error deleting {f}: {e}")
    return Redirect('/')

# Global model cache
model = None

def get_model():
    global model
    if model is None:
        print("Loading Whisper model...")
        model = whisper.load_model("base")
    return model

def generate_transcript_html(segments, filename):
    segments_html = []
    
    for i, segment in enumerate(segments):
        start = segment["start"]
        text = segment["text"]
        # Format time as MM:SS
        minutes = int(start // 60)
        seconds = int(start % 60)
        time_str = f"[{minutes:02d}:{seconds:02d}]"
        
        segments_html.append(
            Div(
                Span(time_str, 
                        style="color:var(--accent); cursor:pointer; font-family:monospace; margin-right:8px; user-select:none;",
                        onclick=f"seekTo({start})",
                        contenteditable="false"),
                Span(text, 
                     style="color:var(--text); cursor:text; padding: 2px;",
                     contenteditable="true",
                     hx_post=f"/update_segment?filename={filename}&index={i}",
                     hx_trigger="blur",
                     hx_swap="none",
                     hx_vals="js:{text: event.target.innerText}"),
                style="margin-bottom:8px; padding:4px; border-radius:4px; transition: background 0.2s;",
                onmouseover="this.style.background='var(--glass)'",
                onmouseout="this.style.background='transparent'"
            )
        )

    return Div(
        H3("Transcription Result:", style="font-weight:700; margin-bottom:10px;"),
        # Container for segments
        Div(
            *segments_html,
            id="transcription-text",
            style="flex:1; overflow-y:auto; padding:12px; background:rgba(0,0,0,0.2); border-radius:8px; border:1px solid var(--border);"
        ),
        Button("Copy Text", 
                onclick=f"copyToClipboard('transcription-text')", 
                cls="btn ghost",
                style="width:100%; margin-top:10px; flex-shrink:0;"),
        # Toggle Subtitles Button
        Button("Show Subtitles on Video", 
               onclick="toggleSubtitles()",
               id="subtitle-toggle-btn",
               cls="btn secondary",
               style="width:100%; margin-top:10px; flex-shrink:0;"),
        
        # Burn Subtitles Button
        Button("🔥 Burn & Download Video", 
               hx_post=f"/burn_subtitles?filename={filename}",
               hx_target="body",
               hx_indicator="#burning-indicator",
               cls="btn warn",
               style="width:100%; margin-top:10px; flex-shrink:0;"),
        Div(
            "Burning subtitles... (this may take a while)",
            id="burning-indicator",
            cls="htmx-indicator muted",
            style="margin-top:10px; text-align: center;"
        ),

        # Inject segments data
        Script(f"window.transcriptSegments = {json.dumps(segments)};"),
        style="margin-top:10px; width:100%; flex:1; display:flex; flex-direction:column; min-height:0;"
    )

def generate_srt(segments):
    srt_content = ""
    for i, segment in enumerate(segments, start=1):
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()
        
        # Format time: HH:MM:SS,mmm
        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds - int(seconds)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            
        srt_content += f"{i}\n{format_time(start)} --> {format_time(end)}\n{text}\n\n"
    return srt_content

@rt('/burn_subtitles')
async def post(filename: str):
    video_path = upload_dir / filename
    json_path = video_path.with_suffix(".transcription.json")
    
    if not video_path.exists() or not json_path.exists():
        return Titled("Error", Div("Video or transcription not found. Please transcribe first."))
    
    try:
        # Load segments
        with open(json_path, "r") as f:
            segments = json.load(f)
            
        # Generate SRT
        srt_content = generate_srt(segments)
        srt_path = video_path.with_suffix(".srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
            
        # Generate Output Filename
        output_filename = f"{video_path.stem}_subtitled{video_path.suffix}"
        output_path = upload_dir / output_filename
        
        # FFmpeg Burn Command
        # Note: 'subtitles' filter requires escaping special characters in path on some systems, 
        # but locally usually fine with absolute path or relative if simple.
        # Ensure srt_path is string.
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", video_path.name,
            "-vf", f"subtitles='{srt_path.name}'", 
            "-c:a", "copy", 
            output_path.name
        ]
        
        # Run in upload_dir to make relative path work easily for subtitles filter
        subprocess.run(cmd, check=True, cwd=str(upload_dir))
        
        # Extract audio for the new file to prevent errors if we edit it again
        extract_audio(output_path)
        
        return Redirect(f'/editor?filename={output_filename}&parent={filename}')
        
    except Exception as e:
        print(f"Burn error: {e}")
        return Titled("Error", Div(f"Failed to burn subtitles: {e}"))

@rt('/update_segment')
def post(filename: str, index: int, text: str):
    json_path = (upload_dir / filename).with_suffix(".transcription.json")
    if not json_path.exists():
        return
    
    try:
        with open(json_path, "r") as f:
            segments = json.load(f)
        
        if 0 <= index < len(segments):
            segments[index]["text"] = text
            
            with open(json_path, "w") as f:
                json.dump(segments, f)
                
        # Return nothing or checkmark? For now nothing, just 200 OK
        return Response(status_code=200)
    except Exception as e:
        print(f"Update segment error: {e}")
        return Response(status_code=500)

@rt('/transcribe')
def post(filename: str):
    audio_path = (upload_dir / filename).with_suffix(".mp3")
    if not audio_path.exists():
        return Div("Audio not found", style="color: var(--danger);")
    
    try:
        mdl = get_model()
        mdl = get_model()
        result = mdl.transcribe(str(audio_path))
        
        # Save transcription to JSON
        json_path = (upload_dir / filename).with_suffix(".transcription.json")
        with open(json_path, "w") as f:
            json.dump(result["segments"], f)
        
        return generate_transcript_html(result["segments"], filename)
    except Exception as e:
        print(f"Transcription error: {e}")
        return Div(f"Error: {e}", style="color: var(--danger);")

@rt('/editor')
def get(filename: str, parent: str = None):
    video_url = f"/uploads/{filename}"
    audio_filename = Path(filename).with_suffix(".mp3").name
    audio_url = f"/uploads/{audio_filename}"
    
    return Layout(
        (
            # Left: Controls
            Aside(
                H3("Editing Flow", id="controls-title"),
                Div("Editing Options", cls="title"),
                
                # Option 1
                Div(
                    Div("Select interval", cls="small-pill", style="margin-bottom:8px"),
                    Label("Video interval (s)", for_="start"),
                    Form(
                        Div(
                            Input(id="start-input", name="start", type="number", value="0", step="0.1"),
                            Input(id="end-input", name="end", type="number", value="10", step="0.1"),
                            cls="row"
                        ),
                        Div(
                            Button("Set Current", type="button", id="set-start-btn", cls="btn ghost"),
                            Button("Set Current", type="button", id="set-end-btn", cls="btn ghost"),
                            cls="row", style="margin-top:10px"
                        ),
                        Div(
                            Button("Remove Interval & Preview", cls="big", style="margin-top:10px"),
                            cls="action-block"
                        ),
                        Hidden(name="filename", value=filename),
                        hx_post="/cut", hx_target="body", hx_indicator="#processing-indicator"
                    ),
                    cls="field"
                ),
                
                # Option 2
                Div(
                    Div("Remove silences", cls="small-pill", style="margin-bottom:8px"),
                    Form(
                        Label("Silence Sensitivity (dB)", for_="threshold"),
                        Div(
                            Input(type="range", name="threshold", min="-60", max="20", value="-30", 
                                  oninput="this.nextElementSibling.innerText = this.value + ' dB'"),
                            Div("-30 dB", cls="small-pill", style="width: 60px; text-align: center;"),
                            cls="slider-wrap"
                        ),
                        
                        Label("Minimum Silence Duration (s)", for_="min_duration", style="margin-top:10px"),
                        Div(
                            Input(type="number", name="min_duration", min="0.1", max="2.0", step="0.1", value="0.2", cls="input"), 
                            cls="row"
                        ),

                        Div("Higher values remove more noise (more aggressive). Lower values preserve more sound.", cls="muted", style="margin-top:8px"),
                        Div(
                            Button("Auto Cut Silence (AI)", cls="btn primary"),
                            style="margin-top:10px"
                        ),
                        Hidden(name="filename", value=filename),
                        hx_post="/autocut_silence", hx_target="body", hx_indicator="#processing-indicator"
                    ),
                     cls="field"
                ),
                
                # Option 3
                Div(
                    Div("Adjust volume", cls="small-pill", style="margin-bottom:8px"),
                     Form(
                        Label("Audio Gain (Volume)", for_="factor"),
                        Div(
                            Input(type="number", name="factor", step="0.1", value="1.0", cls="input"),
                            Div("1.0x", cls="small-pill"),
                            cls="row"
                        ),
                        Div(
                            Button("Apply Volume", cls="btn primary"),
                            style="margin-top:10px"
                        ),
                        Hidden(name="filename", value=filename),
                        hx_post="/apply_volume", hx_target="body", hx_indicator="#processing-indicator"
                    ),
                    cls="field"
                ),
                
                # Processing Indicator
                Div(
                     Div(style="display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--accent); animation: pulse 1s infinite; margin-right:8px;"),
                     Span("Processing..."),
                     id="processing-indicator",
                     cls="htmx-indicator",
                     style="margin-top: 10px; color: var(--accent);"
                ),
                
                cls="panel controls",
                aria_labelledby="controls-title"
            ),
            
            # Center: Preview
            Section(
                H3("Preview", id="preview-title"),
                Div("Preview & Waveform", cls="title"),
                Div(f"Loaded file: {filename}", cls="muted"),
                
                Div(
                    Div(
                        Video(src=video_url, controls=False, id="video-player", style="width:100%; height:100%; object-fit:contain;"),
                        Div("", id="subtitle-overlay"), # Subtitle Overlay moved inside
                        cls="player", 
                        role="region", 
                        aria_label="Video preview",
                    ),
                    # Control Bar
                    Div(
                        Button("▶ Play / Pause", onclick="togglePlay()", id="play-btn", cls="btn secondary", style="width:100%; margin-top:8px; display:flex; align-items:center; justify-content:center; gap:8px;"),
                        cls="controls-bar"
                    ),
                    cls="video-area",
                    style="flex-direction:column; align-items:stretch;"
                ),
                
                Div(
                    Div("Current Time: 00:00", id="time-display", cls="muted"),
                    cls="meta-row",
                    style="margin-top:10px"
                ),
                
                Div(id="waveform", cls="wave", style="margin-top:12px"),
                
                Div(
                    A("Undo Last Cut", href=f"/editor?filename={parent}", cls="btn warn") if parent else None,
                    A("Download Video", href=video_url, download=filename, cls="btn primary"),
                    style="margin-top:12px; display:flex; justify-content:flex-end; gap: 10px;"
                ),
                
                cls="panel preview",
                aria_labelledby="preview-title"
            ),
            
            # Right: Transcription
            Aside(
                H3("Transcription", id="trans-title"),
                Div("Captions & Text", cls="title"),
                
                # Check for existing transcription
                (
                    lambda: generate_transcript_html(json.load(open(upload_dir / f"{Path(filename).stem}.transcription.json")), filename) 
                    if (upload_dir / f"{Path(filename).stem}.transcription.json").exists() else
                    Div(
                        Div("🎙️", style="font-size:24px"),
                        Div("No transcription yet", cls="muted"),
                        Div("Click below to generate captions automatically.", cls="muted"),
                        Div(
                            Button("Transcribe Audio", cls="btn primary",
                                   hx_post=f"/transcribe?filename={filename}", 
                                   hx_target="#trans-container", 
                                   hx_indicator="#loading-transcript")
                        ),
                         Div(
                            "Transcribing... (this may take a while)",
                            id="loading-transcript",
                            cls="htmx-indicator muted",
                            style="margin-top:10px;"
                         ),
                        id="trans-container",
                        cls="empty"
                    )
                )(),
                
                cls="panel transcript",
                aria_labelledby="trans-title"
            ),
            
            # Scripts
            Script(src="https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.min.js"),
            Script(f"""
                const video = document.getElementById('video-player');
                const playBtn = document.getElementById('play-btn');
                
                // Toggle Play Function
                window.togglePlay = function() {{
                    if (video.paused) {{
                        video.play();
                    }} else {{
                        video.pause();
                    }}
                }};
                
                video.addEventListener('play', () => {{
                    playBtn.innerText = "⏸ Pause";
                    wavesurfer.play();
                }});
                
                video.addEventListener('pause', () => {{
                    playBtn.innerText = "▶ Play";
                    wavesurfer.pause();
                }});
                
                // Initialize WaveSurfer
                console.log("Initializing WaveSurfer with: {audio_url}");
                const wavesurfer = WaveSurfer.create({{
                    container: '#waveform',
                    waveColor: '#4f46e5', /* More opaque/vibrant color */
                    progressColor: '#a5b4fc', /* Lighter progress color */
                    url: '{audio_url}',
                    height: 90,
                    barWidth: 3, /* Thicker bars */
                    barGap: 3,
                    barRadius: 3,
                    cursorColor: '#fff',
                    cursorWidth: 2,
                    normalize: true, /* Normalize waveform to fill height */
                }});
                
                wavesurfer.on('ready', () => {{
                    console.log("WaveSurfer is ready");
                    wavesurfer.setVolume(0);
                }});
                
                wavesurfer.on('error', (e) => {{
                    console.error("WaveSurfer Error:", e);
                }});
                
                // Sync Video -> Waveform
                video.addEventListener('timeupdate', () => {{
                    if (!wavesurfer.isPlaying()) {{
                         wavesurfer.setTime(video.currentTime);
                    }}
                    
                    // Update time display
                    const time = video.currentTime;
                    const minutes = Math.floor(time / 60);
                    const seconds = Math.floor(time % 60);
                    const timeStr = `${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
                    const display = document.getElementById('time-display');
                    if (display) display.innerText = `Current Time: ${{timeStr}}`;
                }});
                
                // Sync Waveform -> Video
                wavesurfer.on('interaction', () => {{
                    video.currentTime = wavesurfer.getCurrentTime();
                    // video.play(); // Auto play removed as per user request
                }});
                
                document.getElementById('set-start-btn').onclick = () => {{
                    document.getElementById('start-input').value = video.currentTime.toFixed(1);
                }};
                document.getElementById('set-end-btn').onclick = () => {{
                    document.getElementById('end-input').value = video.currentTime.toFixed(1);
                }};

                window.copyToClipboard = function(elementId) {{
                    const container = document.getElementById(elementId);
                    let textToCopy = "";
                    
                    // Select all editable spans (text only)
                    const spans = container.querySelectorAll('span[contenteditable="true"]');
                    if (spans.length > 0) {{
                        spans.forEach(span => {{
                            textToCopy += span.innerText + "\\n";
                        }});
                    }} else {{
                        // Fallback: grab everything if no segments found
                        textToCopy = container.innerText;
                    }}

                    const copyBtn = document.querySelector(`button[onclick="copyToClipboard('${{elementId}}')"]`);
                    const originalText = copyBtn ? copyBtn.innerText : "Copy Text";

                    const success = () => {{
                        if(copyBtn) {{
                            copyBtn.innerText = "Copied!";
                            setTimeout(() => {{
                                copyBtn.innerText = originalText;
                            }}, 2000);
                        }}
                    }};

                    // Try modern API
                    if (navigator.clipboard && navigator.clipboard.writeText) {{
                        navigator.clipboard.writeText(textToCopy).then(success).catch(err => {{
                            console.error('Async: Could not copy text: ', err);
                            fallbackCopy(textToCopy);
                        }});
                    }} else {{
                        fallbackCopy(textToCopy);
                    }}
                    
                    function fallbackCopy(text) {{
                        var textArea = document.createElement("textarea");
                        textArea.value = text;
                        textArea.style.top = "0";
                        textArea.style.left = "0";
                        textArea.style.position = "fixed";
                        document.body.appendChild(textArea);
                        textArea.focus();
                        textArea.select();
                        try {{
                            var successful = document.execCommand('copy');
                            if(successful) success();
                        }} catch (err) {{
                            console.error('Fallback: unable to copy', err);
                            alert('Failed to copy');
                        }}
                        document.body.removeChild(textArea);
                    }}
                }};
                
                window.seekTo = function(seconds) {{
                    const video = document.getElementById('video-player');
                    video.currentTime = seconds;
                    wavesurfer.setTime(seconds); // Ensure waveform updates immediately
                    // video.play(); // Removed auto-play
                }};

                // Subtitle Logic
                window.showSubtitles = false;
                window.displaySubtitle = function() {{
                    const video = document.getElementById('video-player');
                    const overlay = document.getElementById('subtitle-overlay');
                    
                    if (!window.showSubtitles || !window.transcriptSegments) {{
                        overlay.style.display = 'none';
                        return;
                    }}

                    const currentTime = video.currentTime;
                    // Find active segment
                    const segment = window.transcriptSegments.find(s => currentTime >= s.start && currentTime < s.end);
                    
                    if (segment) {{
                        overlay.innerText = segment.text;
                        overlay.style.display = 'block';
                    }} else {{
                        overlay.style.display = 'none';
                    }}
                }};
                
                window.toggleSubtitles = function() {{
                    window.showSubtitles = !window.showSubtitles;
                    const btn = document.getElementById('subtitle-toggle-btn');
                    if (btn) {{
                        if (window.showSubtitles) {{
                            btn.classList.remove('secondary');
                            btn.classList.add('primary');
                            btn.innerText = "Hide Subtitles";
                        }} else {{
                            btn.classList.remove('primary');
                            btn.classList.add('secondary');
                            btn.innerText = "Show Subtitles on Video";
                        }}
                    }}
                    window.displaySubtitle();
                }};

                // Hook into timeupdate
                video.addEventListener('timeupdate', () => {{
                     window.displaySubtitle();
                }});
            """),
        )
    )

if __name__ == "__main__":
    serve()
