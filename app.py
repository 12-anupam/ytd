from flask import Flask, render_template, request, send_file, jsonify
import os
from yt_dlp import YoutubeDL
import logging
import re
import threading

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Temporary folder to store downloaded files
TEMP_FOLDER = os.path.join(os.getcwd(), "temp_downloads")
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

# Cleanup function to remove old files
def cleanup_temp_files():
    for filename in os.listdir(TEMP_FOLDER):
        file_path = os.path.join(TEMP_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")

# Run cleanup at startup
cleanup_temp_files()

# Function to sanitize file names
def sanitize_filename(filename):
    sanitized = re.sub(r'[\\/*?:"<>|#]', "_", filename)
    sanitized = sanitized.replace(" ", "_")
    return sanitized[:100]  # Limit filename length

# Function to download YouTube video
def download_youtube_video(url, quality):
    try:
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_FOLDER, '%(title)s.%(ext)s'),
            'format': f'bestvideo[height<={quality}]+bestaudio/best' if quality != "best" else 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'quiet': True,
            'no_warnings': True,
            'no_check_certificate': True,
            'force_generic_extractor': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # Ensure the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Downloaded file not found at: {file_path}")
            
            return file_path
    except Exception as e:
        logging.error(f"Error downloading YouTube video: {e}")
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
            file_name = os.path.basename(file_path)
            sanitized_file_name = sanitize_filename(file_name)
            sanitized_file_path = os.path.join(TEMP_FOLDER, sanitized_file_name)

            if file_path != sanitized_file_path:
                os.rename(file_path, sanitized_file_path)

            return jsonify({
                "success": True, 
                "file_name": sanitized_file_name,
                "original_name": os.path.basename(file_path)
            })
        except Exception as e:
            logging.error(f"Error in download: {e}")
            return jsonify({"error": str(e)}), 500

    return render_template("index.html")

@app.route("/download/<file_name>")
def download_file(file_name):
    file_path = os.path.join(TEMP_FOLDER, file_name)
    
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return jsonify({"error": "File not found"}), 404

    try:
        # Schedule file deletion after download completes
        def delete_file():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.debug(f"Deleted file: {file_path}")
            except Exception as e:
                logging.error(f"Error deleting file: {e}")

        response = send_file(
            file_path,
            as_attachment=True,
            download_name=file_name,
            mimetype='video/mp4'
        )

        # Start a timer to delete the file after 5 minutes if not downloaded
        timer = threading.Timer(300, delete_file)
        timer.start()

        return response
    except Exception as e:
        logging.error(f"Error serving file: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
