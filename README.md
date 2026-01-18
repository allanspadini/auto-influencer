# Auto Influencer

Auto Influencer is an AI-powered video editor designed to streamline the content creation process. It automatically removes silences, adjusts audio levels, and prepares your content for fast publishing, all within a sleek, dark-themed web interface.

## Features

- **Smart Silence Removal:** Automatically detects and removes silent segments from your videos with customizable sensitivity (dB) and duration thresholds.
- **Precision Trimming:** Manually select and remove specific intervals from your video.
- **Audio Enhancement:** Adjust the global volume gain of your video.
- **AI Transcription:** Uses OpenAI Whisper locally to generate accurate transcripts of your video audio.
- **Subtitle Generation:** Automatically generates subtitles from transcripts.
- **Burn-in Subtitles:** Hardcode (burn) subtitles directly into the video file for social media compatibility.
- **Dark Mode UI:** A premium, eye-friendly interface designed for extended editing sessions.

## 🛠 Prerequisites

- **Python 3.10+**
- **uv** (An extremely fast Python package and project manager)
- **FFmpeg** (Required for video processing)

## 🚀 How to Run

This project uses `uv` for dependency management.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/allanspadini/auto-influencer.git
    cd auto-influencer
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

3.  **Run the application:**
    ```bash
    uv run python main.py
    ```

4.  **Access the Editor:**
    Open your browser and navigate to `http://localhost:5001` (or the port displayed in your terminal).

## Technologies

- **FastHTML:** For the modern, reactive web interface.
- **MoviePy & ImageIO-FFmpeg:** For powerful video and audio processing.
- **OpenAI Whisper:** For state-of-the-art local speech recognition.
