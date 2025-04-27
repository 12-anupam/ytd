from flask import Flask, render_template, request, send_file, jsonify
import os
from yt_dlp import YoutubeDL
import logging
import re
import threading
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TEMP_FOLDER = os.path.join(os.getcwd(), "temp_downloads")
os.makedirs(TEMP_FOLDER, exist_ok=True)

def sanitize_filename(filename):
    """Sanitize filename and ensure .mp4 extension"""
    filename = re.sub(r'[\\/*?:"<>|#]', "_", filename)
    filename = filename.replace(" ", "_")
    if not filename.lower().endswith('.mp4'):
        filename += '.mp4'
    return filename[:100]  # Limit filename length

def download_youtube_video(url, quality):
    try:
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_FOLDER, '%(title)s.%(ext)s'),
            'format': f'bestvideo[height<={quality}]+bestaudio/best' if quality != "best" else 'best',
            'merge_output_format': 'mp4',
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                },
                {
                    'key': 'FFmpegMetadata'
                }
            ],
            'quiet': False,
            'no_warnings': False,
            'logger': logger,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # Ensure the file has .mp4 extension
            if not file_path.lower().endswith('.mp4'):
                new_path = os.path.splitext(file_path)[0] + '.mp4'
                os.rename(file_path, new_path)
                file_path = new_path
            
            return file_path
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        quality = request.form.get("quality", "best")

        if not url:
            return jsonify({"error": "URL is required"}), 400

        try:
            file_path = download_youtube_video(url, quality)
            file_name = sanitize_filename(os.path.basename(file_path))
            sanitized_file_path = os.path.join(TEMP_FOLDER, file_name)

            if file_path != sanitized_file_path:
                os.rename(file_path, sanitized_file_path)

            return jsonify({
                "success": True, 
                "file_name": file_name
            })
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return render_template("index.html")

@app.route("/download/<file_name>")
def download_file(file_name):
    file_path = os.path.join(TEMP_FOLDER, file_name)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    try:
        # Schedule file deletion after 1 hour
        def delete_file():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")

        timer = threading.Timer(3600, delete_file)
        timer.start()

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_name,
            mimetype='video/mp4'
        )
    except Exception as e:
        logger.error(f"Error serving file: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
