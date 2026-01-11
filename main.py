from fasthtml.common import *
from monsterui.all import *
import shutil
import os
import subprocess
from pathlib import Path
from starlette.staticfiles import StaticFiles
import imageio_ffmpeg
import whisper

# Setup
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

# Theme/Headers
hdrs = (
    Theme.blue.headers()
)

app, rt = fast_app(hdrs=hdrs)

def Layout(content):
    return (
        Title("Auto Influencer"),
        Body(
            Container(
                H1("Auto Influencer", cls="text-4xl font-bold mb-4"),
                Div(content, cls="py-4"),
                cls="container mx-auto p-4 max-w-7xl"
            ),
            cls="bg-background text-foreground min-h-screen"
        )
    )

@rt('/')
def get():
    return Layout(
        Card(
            H3("Upload Video", cls="text-2xl font-bold mb-2"),
            P("Select a video file to begin editing.", cls=TextPresets.muted_sm),
            Form(
                Input(type="file", name="video", accept="video/*", required=True, cls="mb-4"),
                Button("Upload", cls=ButtonT.primary),
                action="/upload", method="post", enctype="multipart/form-data"
            ),
            cls="max-w-md mx-auto mt-10 p-6"
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
    new_filename = f"{original_name}_cut_{int(start)}_{int(end)}{extension}"
    output_path = video_path.parent / new_filename
    
    # FFmpeg cut command
    # -i input -ss start -to end -c copy output
    # Note: placing -ss before -i is faster but might be less accurate keyframe-wise. 
    # For a basic editor, re-encoding might be better for accuracy, but slower.

    # We will use re-encoding to be safe with cuts: -c:v libx264 -c:a aac
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", 
        "-i", str(video_path),
        "-ss", str(start),
        "-to", str(end),
        "-c:v", "libx264", "-c:a", "aac",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)
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

@rt('/transcribe')
def post(filename: str):
    audio_path = (upload_dir / filename).with_suffix(".mp3")
    if not audio_path.exists():
        return Div("Audio not found", cls="text-red-500")
    
    try:
        mdl = get_model()
        result = mdl.transcribe(str(audio_path))
        
        # Create interactive segments
        segments_html = []
        full_text = result["text"] # Keep full text for copy button
        
        for segment in result["segments"]:
            start = segment["start"]
            text = segment["text"]
            # Format time as MM:SS
            minutes = int(start // 60)
            seconds = int(start % 60)
            time_str = f"[{minutes:02d}:{seconds:02d}]"
            
            segments_html.append(
                Div(
                    Span(time_str, 
                         cls="text-blue-400 cursor-pointer hover:text-blue-300 font-mono mr-2 select-none", 
                         onclick=f"seekTo({start})"),
                    Span(text, cls="text-gray-100"),
                    cls="mb-2 hover:bg-gray-800 rounded p-1 transition-colors"
                )
            )

        return Div(
            H3("Transcription Result:", cls="font-bold mb-2"),
            # Container for segments
            Div(
                *segments_html,
                id="transcription-text", # ID kept for copy function (will copy inner text of all children)
                cls="h-64 overflow-y-auto p-4 bg-gray-900 text-white rounded-lg border border-gray-700 custom-scrollbar"
            ),
            Button("Copy Text", 
                   onclick=f"copyToClipboard('transcription-text')", 
                   cls="mt-2 w-full " + ButtonT.secondary),
            cls="mt-4"
        )
    except Exception as e:
        print(f"Transcription error: {e}")
        return Div(f"Error: {e}", cls="text-red-500")

@rt('/editor')
def get(filename: str, parent: str = None):
    video_url = f"/uploads/{filename}"
    audio_filename = Path(filename).with_suffix(".mp3").name
    audio_url = f"/uploads/{audio_filename}"
    
    return Layout(
        Div(
            H2(f"Editing: {filename}", cls="text-3xl font-bold mb-4"),
            Div(
                A("New Project", href="/", cls=ButtonT.ghost + " h-12 px-6 flex items-center justify-center"),
                Form(
                    Button("Clean Project", cls="bg-red-600 hover:bg-red-700 text-white h-12 px-6 rounded-lg"),
                    action="/clean", method="post",
                    cls="inline-block"
                ),
                cls="flex gap-2 mb-4 items-center"
            ),
            
            Div(
                # Left Column: Video Editor
                Div(
                    # Video Player
                    Video(src=video_url, controls=True, id="video-player", cls="w-full rounded-lg shadow-lg mb-4"),
                    
                    # Waveform Container
                    Div(id="waveform", cls="w-full bg-card p-4 rounded-lg shadow-inner mb-4"),
                    
                    # Controls area
                    Card(
                        Form(
                            Hidden(id="filename", name="filename", value=filename),
                            Div(
                                Div(
                                    Label("Start Time (s)", cls="label"),
                                    Input(id="start-input", name="start", type="number", step="0.1", value="0", cls="input input-bordered w-full"),
                                    Button("Set Current", type="button", id="set-start-btn", cls="mt-1 " + ButtonT.secondary),
                                    cls="flex flex-col gap-1"
                                ),
                                Div(
                                    Label("End Time (s)", cls="label"),
                                    Input(id="end-input", name="end", type="number", step="0.1", value="10", cls="input input-bordered w-full"),
                                    Button("Set Current", type="button", id="set-end-btn", cls="mt-1 " + ButtonT.secondary),
                                    cls="flex flex-col gap-1"
                                ),
                                cls="grid grid-cols-2 gap-4 mb-4"
                            ),
                            Button("Cut & Preview", cls="w-full " + ButtonT.primary),
                            action="/cut", method="post"
                        ),
                        Div(
                            A("Undo Last Cut", href=f"/editor?filename={parent}", cls="w-full " + ButtonT.destructive + " text-center block h-12 flex items-center justify-center") if parent else None,
                            A("Download Video", href=video_url, download=filename, cls="w-full " + ButtonT.secondary + " text-center block h-12 flex items-center justify-center"),
                            cls="flex flex-col gap-2 mt-2"
                        ),
                        cls="p-4"
                    ),
                    cls="col-span-2"
                ),
                # Right Column: Transcription
                Card(
                     H3("Transcription", cls="text-xl font-bold mb-4"),
                     Button("Transcribe Audio", 
                            hx_post=f"/transcribe?filename={filename}", 
                            hx_target="#transcription-result", 
                            hx_indicator="#loading-transcript",
                            cls="w-full " + ButtonT.secondary + " mb-4"),
                     Div(
                        Loading(cls=LoadingT.dots, htmx_indicator=True),
                        Span(" Transcribing (this may take a while)...", cls="ml-2 text-sm text-muted-foreground"),
                        id="loading-transcript",
                        cls="htmx-indicator mb-4"
                     ),
                     Div(id="transcription-result", cls="min-h-[200px]"),
                     cls="col-span-1 h-fit"
                ),
                cls="grid grid-cols-1 lg:grid-cols-3 gap-6"
            ),

            # Application State/Scripts
            Script(src="https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.min.js"),
            Script(f"""
                const video = document.getElementById('video-player');
                
                // Initialize WaveSurfer
                // Initialize WaveSurfer
                const wavesurfer = WaveSurfer.create({{
                    container: '#waveform',
                    waveColor: '#4F46E5',
                    progressColor: '#383351',
                    url: '{audio_url}',
                    height: 100,
                }});
                
                // Mute WaveSurfer to avoid double audio
                wavesurfer.setVolume(0);
                
                // Sync Video -> Waveform
                video.addEventListener('play', () => wavesurfer.play());
                video.addEventListener('pause', () => wavesurfer.pause());
                video.addEventListener('timeupdate', () => {{
                    if (!wavesurfer.isPlaying()) {{
                         wavesurfer.setTime(video.currentTime);
                    }}
                }});
                
                // Sync Waveform -> Video
                wavesurfer.on('interaction', () => {{
                    video.currentTime = wavesurfer.getCurrentTime();
                }});
                
                // Set Start/End Buttons
                document.getElementById('set-start-btn').onclick = () => {{
                    document.getElementById('start-input').value = video.currentTime.toFixed(2);
                }};
                document.getElementById('set-end-btn').onclick = () => {{
                    document.getElementById('end-input').value = video.currentTime.toFixed(2);
                }};

                // Robust Copy Function
                window.copyToClipboard = function(elementId) {{
                    const text = document.getElementById(elementId).innerText;
                    
                    // Try modern API
                    if (navigator.clipboard && window.isSecureContext) {{
                        navigator.clipboard.writeText(text).then(() => {{
                            alert('Copied to clipboard!');
                        }}).catch(err => {{
                            console.error('Async: Could not copy text: ', err);
                            fallbackCopyTextToClipboard(text);
                        }});
                    }} else {{
                        fallbackCopyTextToClipboard(text);
                    }}
                }};

                function fallbackCopyTextToClipboard(text) {{
                    var textArea = document.createElement("textarea");
                    textArea.value = text;
                    
                    // Avoid scrolling to bottom
                    textArea.style.top = "0";
                    textArea.style.left = "0";
                    textArea.style.position = "fixed";
                    
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    
                    try {{
                        var successful = document.execCommand('copy');
                        var msg = successful ? 'successful' : 'unsuccessful';
                        if (successful) alert('Copied to clipboard (fallback)!');
                        else alert('Fallback copy failed.');
                    }} catch (err) {{
                        console.error('Fallback: Oops, unable to copy', err);
                        alert('Failed to copy');
                    }}
                    
                    document.body.removeChild(textArea);
                }}

                // Seek Function
                window.seekTo = function(seconds) {{
                    const video = document.getElementById('video-player');
                    video.currentTime = seconds;
                    video.play();
                }};
            """),
            cls="space-y-4"
        )
    )

serve()
