import os
import yt_dlp
import whisper
from flask import Flask, request, jsonify, send_from_directory
from flask import render_template
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import tempfile
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
@app.route('/')
def index():
    return render_template('index.html')
# Progress tracking
progress = {}

def download_youtube_audio(url):
    """Download only audio from YouTube (faster than video)"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], 'yt_%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')

def process_video_to_gifs(video_path, prompt, job_id):
    try:
        progress[job_id] = {'stage': 'transcribing', 'progress': 0}
        
        # Transcribe with Whisper (faster with small models)
        model = whisper.load_model("tiny")
        result = model.transcribe(video_path)
        segments = result["segments"]
        
        progress[job_id] = {'stage': 'creating_gifs', 'progress': 50}
        
        # Create max 3 GIFs
        gif_paths = []
        for i, seg in enumerate(segments[:3]):
            clip = VideoFileClip(video_path).subclip(seg['start'], seg['end'])
            text_clip = TextClip(
                seg['text'], fontsize=24, color='white',
                size=(clip.w*0.9, None), method='caption'
            ).set_position(('center', 'bottom')).set_duration(clip.duration)
            
            final = CompositeVideoClip([clip, text_clip])
            gif_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{i}.gif")
            final.write_gif(gif_path, fps=8)
            gif_paths.append(gif_path)
            
            progress[job_id]['progress'] = 50 + ((i+1)*50/3)
        
        progress[job_id] = {'stage': 'complete', 'progress': 100, 'gifs': gif_paths}
        
    except Exception as e:
        progress[job_id] = {'error': str(e)}
    finally:
        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)

@app.route('/generate', methods=['POST'])
def generate():
    job_id = tempfile.mkstemp()[1][-10:]  # Simple unique ID
    
    if 'youtube_url' in request.form:
        # Start YouTube processing in background
        threading.Thread(
            target=process_video_to_gifs,
            args=(download_youtube_audio(request.form['youtube_url']), 
                 request.form['prompt'],
                 job_id)
        ).start()
    else:
        # Handle direct upload
        file = request.files['video']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        threading.Thread(
            target=process_video_to_gifs,
            args=(filepath, request.form['prompt'], job_id)
        ).start()
    
    return jsonify({'job_id': job_id})

@app.route('/progress/<job_id>')
def get_progress(job_id):
    return jsonify(progress.get(job_id, {'error': 'Job not found'}))

@app.route('/gif/<path:filename>')
def serve_gif(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(threaded=True)