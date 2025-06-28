import os
import whisper
import openai
from flask import Flask, request, jsonify, send_from_directory, render_template
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import tempfile
import threading
from werkzeug.utils import secure_filename
import moviepy.config as mpconf
import re
from datetime import datetime
import yt_dlp
import json
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai 
# Configure ImageMagick path
mpconf.change_settings({
    "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
})

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs('templates', exist_ok=True)

genai.configure(api_key='AIzaSyBwWydwEAt66jKarUSfpAxSnXkAM0KJmtg')

# Progress tracking
progress = {}

# Set your OpenAI API key here (or use environment variable)
# openai.api_key = os.getenv('OPENAI_API_KEY')  # Uncomment and set your API key

def is_youtube_url(url):
    """Check if the URL is a valid YouTube URL"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return youtube_regex.match(url) is not None

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0]
    elif 'watch?v=' in url:
        return url.split('watch?v=')[-1].split('&')[0]
    elif 'embed/' in url:
        return url.split('embed/')[-1].split('?')[0]
    return None

def get_youtube_info_and_transcript(url):
    """Get YouTube video info and transcript without downloading the video"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'json',
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get video duration
            duration = info.get('duration', 0)
            if duration > 900:  # 15 minutes max for YouTube videos
                raise Exception("YouTube video too long. Maximum duration is 15 minutes.")
            
            # Try to get transcript from YouTube's automatic captions
            transcript_segments = []
            
            # Check for automatic subtitles
            auto_subs = info.get('automatic_captions', {})
            if auto_subs:
                # Try English subtitles first
                for lang in ['en', 'en-US', 'en-GB']:
                    if lang in auto_subs:
                        subtitle_info = auto_subs[lang]
                        # Get JSON format subtitle
                        for sub in subtitle_info:
                            if sub.get('ext') == 'json3':
                                # Download subtitle file
                                sub_url = sub['url']
                                import urllib.request
                                with urllib.request.urlopen(sub_url) as response:
                                    sub_data = json.loads(response.read().decode())
                                    
                                    # Parse JSON3 subtitle format
                                    for event in sub_data.get('events', []):
                                        if 'segs' in event:
                                            start_time = event.get('tStartMs', 0) / 1000
                                            duration_ms = event.get('dDurationMs', 0)
                                            
                                            text_parts = []
                                            for seg in event['segs']:
                                                if 'utf8' in seg:
                                                    text_parts.append(seg['utf8'])
                                            
                                            if text_parts:
                                                text = ''.join(text_parts).strip()
                                                if text and len(text) > 5:
                                                    transcript_segments.append({
                                                        'text': text,
                                                        'start': start_time,
                                                        'end': start_time + (duration_ms / 1000)
                                                    })
                                break
                        break
            
            # If no automatic captions, try manual subtitles
            if not transcript_segments:
                subtitles = info.get('subtitles', {})
                if subtitles:
                    for lang in ['en', 'en-US', 'en-GB']:
                        if lang in subtitles:
                            # Similar processing for manual subtitles
                            break
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': duration,
                'transcript_segments': transcript_segments,
                'video_url': info.get('url'),
                'formats': info.get('formats', [])
            }
            
    except Exception as e:
        raise Exception(f"Failed to extract YouTube info: {str(e)}")

def download_youtube_segment(url, start_time, end_time, output_path):
    """Download a specific segment from YouTube video"""
    try:
        # Calculate duration
        duration = end_time - start_time
        
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]',  # Limit quality to save bandwidth
            'outtmpl': output_path,
            'external_downloader': 'ffmpeg',
            'external_downloader_args': [
                '-ss', str(start_time),
                '-t', str(duration)
            ]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        return True
    except Exception as e:
        print(f"Error downloading segment: {e}")
        return False

def analyze_segments_with_ai(segments, prompt):
    """
    Analyze transcript segments using Gemini AI to find the best matches for the prompt.
    If Gemini API is not available, falls back to keyword matching.
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-pro')
        
        # Prepare the transcript text for analysis
        transcript_text = "\n".join([f"{i}: {seg['text']}" for i, seg in enumerate(segments)])
        
        # Create the prompt for Gemini
        analysis_prompt = f"""
        Analyze this video transcript and select the best segments matching the user's prompt.
        Return ONLY the segment numbers (0, 1, 2, etc.) separated by commas, nothing else.
        
        User Prompt: {prompt}
        
        Transcript Segments:
        {transcript_text}
        
        Selected segment numbers:
        """
        
        # Get response from Gemini
        response = model.generate_content(analysis_prompt)
        
        # Extract segment numbers from the response
        if response.text:
            selected_indices = []
            for part in response.text.split(','):
                part = part.strip()
                if part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(segments):
                        selected_indices.append(idx)
            return selected_indices[:3]  # Return max 3 segments
        
    except Exception as e:
        print(f"Gemini API error: {e}")
    
    # Fallback: Simple keyword matching
    prompt_words = prompt.lower().split()
    scored_segments = []
    
    for i, segment in enumerate(segments):
        text = segment['text'].lower()
        score = sum(1 for word in prompt_words if word in text)
        
        # Bonus for emotional words if prompt contains them
        emotional_words = ['funny', 'sad', 'happy', 'angry', 'excited', 'motivational']
        if any(word in prompt.lower() for word in emotional_words):
            if any(word in text for word in emotional_words):
                score += 2
        
        scored_segments.append((i, score, segment))
    
    # Sort by score and return top 3
    scored_segments.sort(key=lambda x: x[1], reverse=True)
    return [seg[0] for seg in scored_segments[:3] if seg[1] > 0]

def process_youtube_to_gifs(youtube_url, prompt, job_id):
    try:
        progress[job_id] = {'stage': 'extracting_info', 'progress': 5}
        
        # Extract video info and transcript
        video_info = get_youtube_info_and_transcript(youtube_url)
        transcript_segments = video_info['transcript_segments']
        
        if not transcript_segments:
            # Fallback: use Whisper on full video (last resort)
            progress[job_id] = {'stage': 'downloading_for_transcription', 'progress': 10}
            temp_video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_full.mp4")
            
            # Download full video for transcription (only if no captions available)
            ydl_opts = {
                'format': 'worst[ext=mp4]/worst',  # Use lowest quality for transcription
                'outtmpl': temp_video_path,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            
            progress[job_id] = {'stage': 'transcribing', 'progress': 20}
            
            # Transcribe with Whisper
            model = whisper.load_model("base")
            result = model.transcribe(temp_video_path)
            transcript_segments = result["segments"]
            
            # Cleanup full video
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
        else:
            progress[job_id] = {'stage': 'analyzing_transcript', 'progress': 20}
        
        if not transcript_segments:
            progress[job_id] = {'error': 'No speech detected in video'}
            return
        
        progress[job_id] = {'stage': 'analyzing_content', 'progress': 30}
        
        # Filter segments (minimum duration 2 seconds, maximum 10 seconds)
        valid_segments = []
        for seg in transcript_segments:
            duration = seg['end'] - seg['start']
            if 2 <= duration <= 10 and len(seg['text'].strip()) > 10:
                valid_segments.append(seg)
        
        if not valid_segments:
            progress[job_id] = {'error': 'No suitable segments found'}
            return
        
        # Use AI to select best segments
        selected_indices = analyze_segments_with_ai(valid_segments, prompt)
        
        if not selected_indices:
            # If no good matches, take first 3 valid segments
            selected_indices = list(range(min(3, len(valid_segments))))
        
        progress[job_id] = {'stage': 'downloading_segments', 'progress': 50}
        
        # Download and create GIFs from selected segments
        gif_paths = []
        total_segments = len(selected_indices)
        
        for i, seg_idx in enumerate(selected_indices):
            try:
                seg = valid_segments[seg_idx]
                
                # Download specific segment
                progress[job_id] = {
                    'stage': f'downloading_segment_{i+1}',
                    'progress': 50 + (i * 30 / total_segments)
                }
                
                # Add padding around segment
                start_time = max(0, seg['start'] - 1)
                end_time = seg['end'] + 1
                
                segment_filename = f"{job_id}_segment_{i}.mp4"
                segment_path = os.path.join(app.config['UPLOAD_FOLDER'], segment_filename)
                
                # Download this specific segment
                if download_youtube_segment(youtube_url, start_time, end_time, segment_path):
                    # Process the downloaded segment
                    clip = VideoFileClip(segment_path)
                    
                    # Resize if too large
                    if clip.w > 480:
                        clip = clip.resize(width=480)
                    
                    # Create text clip
                    text = seg['text'].strip()
                    if len(text) > 60:
                        text = text[:60] + "..."
                    
                    text_clip = TextClip(
                        text,
                        fontsize=max(16, min(24, clip.w // 20)),
                        color='white',
                        size=(clip.w * 0.9, None),
                        method='caption',
                        font='Arial-Bold',
                        stroke_color='black',
                        stroke_width=2
                    ).set_position(('center', 'bottom')).set_duration(clip.duration)
                    
                    final = CompositeVideoClip([clip, text_clip])
                    
                    # Generate GIF
                    gif_filename = f"{job_id}_{i+1}.gif"
                    gif_path = os.path.join(app.config['OUTPUT_FOLDER'], gif_filename)
                    
                    final.write_gif(
                        gif_path,
                        fps=10,
                        program='ffmpeg',
                        opt='optimizeplus'
                    )
                    
                    gif_paths.append({
                        'filename': gif_filename,
                        'text': text,
                        'duration': f"{clip.duration:.1f}s"
                    })
                    
                    # Cleanup
                    clip.close()
                    final.close()
                    if os.path.exists(segment_path):
                        os.remove(segment_path)
                        
                else:
                    print(f"Failed to download segment {i}")
                    continue
                    
                # Update progress
                progress[job_id]['progress'] = 50 + ((i + 1) * 40 / total_segments)
                
            except Exception as e:
                print(f"Error creating GIF {i}: {e}")
                continue
        
        if gif_paths:
            progress[job_id] = {
                'stage': 'complete',
                'progress': 100,
                'gifs': gif_paths,
                'total_gifs': len(gif_paths),
                'video_title': video_info.get('title', 'Unknown')
            }
        else:
            progress[job_id] = {'error': 'Failed to create any GIFs'}
            
    except Exception as e:
        progress[job_id] = {'error': f'Processing failed: {str(e)}'}

def process_video_to_gifs(video_path, prompt, job_id):
    try:
        progress[job_id] = {'stage': 'loading_video', 'progress': 10}
        
        # Load video first to check duration and validity
        video = VideoFileClip(video_path)
        if video.duration > 600:  # 10 minutes max
            progress[job_id] = {'error': 'Video too long. Maximum duration is 10 minutes.'}
            return
        
        progress[job_id] = {'stage': 'transcribing', 'progress': 20}
        
        # Transcribe with Whisper
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        segments = result["segments"]
        
        if not segments:
            progress[job_id] = {'error': 'No speech detected in video'}
            return
        
        progress[job_id] = {'stage': 'analyzing_content', 'progress': 40}
        
        # Filter segments (minimum duration 2 seconds, maximum 10 seconds)
        valid_segments = []
        for seg in segments:
            duration = seg['end'] - seg['start']
            if 2 <= duration <= 10 and len(seg['text'].strip()) > 10:
                valid_segments.append(seg)
        
        if not valid_segments:
            progress[job_id] = {'error': 'No suitable segments found'}
            return
        
        # Use AI to select best segments
        selected_indices = analyze_segments_with_ai(valid_segments, prompt)
        
        if not selected_indices:
            # If no good matches, take first 3 valid segments
            selected_indices = list(range(min(3, len(valid_segments))))
        
        progress[job_id] = {'stage': 'creating_gifs', 'progress': 60}
        
        # Create GIFs from selected segments
        gif_paths = []
        for i, seg_idx in enumerate(selected_indices):
            try:
                seg = valid_segments[seg_idx]
                
                # Create video clip with some padding
                start_time = max(0, seg['start'] - 0.5)
                end_time = min(video.duration, seg['end'] + 0.5)
                
                clip = video.subclip(start_time, end_time)
                
                # Resize if too large
                if clip.w > 480:
                    clip = clip.resize(width=480)
                
                # Create text clip with better formatting
                text = seg['text'].strip()
                if len(text) > 60:
                    text = text[:60] + "..."
                
                text_clip = TextClip(
                    text,
                    fontsize=max(16, min(24, clip.w // 20)),
                    color='white',
                    size=(clip.w * 0.9, None),
                    method='caption',
                    font='Arial-Bold',
                    stroke_color='black',
                    stroke_width=2
                ).set_position(('center', 'bottom')).set_duration(clip.duration)
                
                final = CompositeVideoClip([clip, text_clip])
                
                # Generate GIF
                gif_filename = f"{job_id}_{i+1}.gif"
                gif_path = os.path.join(app.config['OUTPUT_FOLDER'], gif_filename)
                
                final.write_gif(
                    gif_path,
                    fps=10,
                    program='ffmpeg',
                    opt='optimizeplus'
                )
                
                gif_paths.append({
                    'filename': gif_filename,
                    'text': text,
                    'duration': f"{clip.duration:.1f}s"
                })
                
                # Update progress
                progress[job_id]['progress'] = 60 + ((i + 1) * 30 / len(selected_indices))
                
                # Cleanup clips
                clip.close()
                final.close()
                
            except Exception as e:
                print(f"Error creating GIF {i}: {e}")
                continue
        
        video.close()
        
        if gif_paths:
            progress[job_id] = {
                'stage': 'complete',
                'progress': 100,
                'gifs': gif_paths,
                'total_gifs': len(gif_paths)
            }
        else:
            progress[job_id] = {'error': 'Failed to create any GIFs'}
            
    except Exception as e:
        progress[job_id] = {'error': f'Processing failed: {str(e)}'}
    finally:
        # Cleanup uploaded file
        if os.path.exists(video_path):
            os.remove(video_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        prompt = request.form.get('prompt', '').strip()
        youtube_url = request.form.get('youtube_url', '').strip()
        
        if not prompt:
            return jsonify({'error': 'Please provide a prompt'}), 400
        
        # Generate unique job ID
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + tempfile.mkstemp()[1][-6:]
        
        # Check if YouTube URL is provided
        if youtube_url:
            # Validate YouTube URL
            if not is_youtube_url(youtube_url):
                return jsonify({'error': 'Invalid YouTube URL'}), 400
            
            # Start YouTube processing
            threading.Thread(
                target=process_youtube_to_gifs,
                args=(youtube_url, prompt, job_id)
            ).start()
            
            return jsonify({
                'job_id': job_id,
                'message': 'YouTube processing started. Check progress using the job ID.',
                'source': 'youtube'
            })
        
        # Check if video file is uploaded
        elif 'video' in request.files and request.files['video'].filename != '':
            file = request.files['video']
            
            # Validate file type
            allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                return jsonify({'error': 'Invalid file type. Please upload MP4, AVI, MOV, MKV, or WEBM'}), 400
            
            # Save uploaded file
            filename = secure_filename(f"{job_id}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Start file processing
            threading.Thread(
                target=process_video_to_gifs,
                args=(filepath, prompt, job_id)
            ).start()
            
            return jsonify({
                'job_id': job_id,
                'message': 'File processing started. Check progress using the job ID.',
                'source': 'upload'
            })
        
        # Neither YouTube URL nor file provided
        else:
            return jsonify({
                'error': 'Please provide either a YouTube URL or upload a video file'
            }), 400
        
    except Exception as e:
        return jsonify({'error': f'Request failed: {str(e)}'}), 500
    
@app.route('/progress/<job_id>')
def get_progress(job_id):
    return jsonify(progress.get(job_id, {'error': 'Job not found'}))

@app.route('/download/<filename>')
def download_gif(filename):
    try:
        return send_from_directory(
            app.config['OUTPUT_FOLDER'],
            filename,
            as_attachment=True
        )
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up old files to save space"""
    try:
        # Remove files older than 1 hour
        import time
        current_time = time.time()
        
        for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    if current_time - os.path.getmtime(filepath) > 3600:  # 1 hour
                        os.remove(filepath)
        
        return jsonify({'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(threaded=True, debug=True, port=5000)