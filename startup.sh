#!/bin/bash
# Install ffmpeg if not already present
if ! command -v ffmpeg &> /dev/null
then
    echo "Installing ffmpeg..."
    apt-get update && apt-get install -y ffmpeg
fi

# Start the application
gunicorn --bind 0.0.0.0:$PORT app:app
