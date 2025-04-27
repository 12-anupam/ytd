from flask import Flask, render_template, request, send_file, jsonify
import os
from yt_dlp import YoutubeDL
import logging
import re

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TEMP_FOLDER = os.path.join(os.getcwd(), "temp_downloads")
os.makedirs(TEMP_FOLDER, exist_ok=True)

def sanitize_filename(filename):
    """Ensure filename ends with .mp4"""
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    if not filename.lower().endswith('.mp4'):
        filename = os.path.splitext(filename)[0] + '.mp4'
    return filename[:150]  # Limit length

def download_video(url, quality):
    ydl_opts = {
        'outtmpl': os.path.join(TEMP_FOLDER, '%(title)s.%(ext)s'),
        'format': f'bestvideo[height<={quality}]+bestaudio/best' if quality != "best" else 'best',
        'merge_output_format': 'mp4',
        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            },
            {'key': 'FFmpegMetadata'}
        ],
        'logger': logger,
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        
        # Ensure MP4 extension
        if not filepath.lower().endswith('.mp4'):
            new_path = os.path.splitext(filepath)[0] + '.mp4'
            os.rename(filepath, new_path)
            filepath = new_path
            
        return filepath

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
            return jsonify({"error": str(e)}), 500
            
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
