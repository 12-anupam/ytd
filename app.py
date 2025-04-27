from flask import Flask, render_template, request, send_file, jsonify
import os
from yt_dlp import YoutubeDL
import logging
import re
import random

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary download folder
TEMP_FOLDER = os.path.join(os.getcwd(), "temp_downloads")
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Rotating User-Agents to avoid YouTube blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def sanitize_filename(filename):
    """Ensure filename is safe and has .mp4 extension"""
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    if not filename.lower().endswith('.mp4'):
        filename = f"{os.path.splitext(filename)[0]}.mp4"
    return filename[:100]  # Limit filename length

def download_video(url, quality):
    ydl_opts = {
        'outtmpl': os.path.join(TEMP_FOLDER, '%(title)s.%(ext)s'),
        'format': f'bestvideo[height<={quality}]+bestaudio/best' if quality != "best" else 'best',
        'merge_output_format': 'mp4',
        'postprocessors': [
            {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},
            {'key': 'FFmpegMetadata'}
        ],
        # Public-friendly headers to avoid 403
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com',
        },
        'extractor_args': {
            'youtube': {
                'skip': ['dash', 'hls'],  # Avoid formats that require auth
            },
        },
        'socket_timeout': 30,
        'retries': 5,
        'throttledratelimit': 1_000_000,  # Avoid rate-limiting
        'ignoreerrors': False,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            
            # Ensure MP4 extension
            if not filepath.lower().endswith('.mp4'):
                new_path = os.path.splitext(filepath)[0] + '.mp4'
                os.rename(filepath, new_path)
                filepath = new_path
            
            return filepath
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        quality = request.form.get("quality", "best")

        if not url:
            return jsonify({"error": "URL is required"}), 400

        try:
            filepath = download_video(url, quality)
            filename = sanitize_filename(os.path.basename(filepath))
            return jsonify({"success": True, "filename": filename})
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return jsonify({"error": "Failed to download video. Try a different URL or quality."}), 500

    return render_template("index.html")

@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join(TEMP_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
