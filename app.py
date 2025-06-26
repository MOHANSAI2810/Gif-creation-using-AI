import os
from flask import Flask, request, render_template, jsonify, send_from_directory
from flask_cors import CORS
import whisper
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import moviepy.config as mpconf
mpconf.change_settings({"IMAGEMAGICK_BINARY": "C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})


app = Flask(__name__)
CORS(app)

# Create folders
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# FFmpeg path (Windows users)
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"  # Update this if needed

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-gif', methods=['POST'])
def generate_gif():
    prompt = request.form.get("prompt", "").strip().lower()
    video_file = request.files.get("video")

    if not video_file or not prompt:
        return jsonify({"error": "Please provide a prompt and video file."}), 400

    # Save the video file
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
    video_file.save(video_path)

    # Check for audio stream
    clip = VideoFileClip(video_path)
    if clip.audio is None:
        return jsonify({"error": "This video has no audio. Please upload a video with speech."}), 400

    # Transcribe using Whisper
    model = whisper.load_model("base")
    result = model.transcribe(video_path)
    segments = result["segments"]

    print("\n🔍 Transcript Preview:\n", result["text"][:300])
    print("\n🧩 Segment Preview:")
    for s in segments[:5]:
        print(f"[{s['start']:.2f}s - {s['end']:.2f}s]: {s['text']}")

    # Define keywords per prompt
    prompt_keywords = {
        "sadness": ["sad", "cry", "tears", "hurt", "lonely", "pain"],
        "funny": ["laugh", "funny", "joke", "hilarious", "comedy"],
        "motivational": ["believe", "win", "success", "never give up", "strong"]
    }

    # Match segments
    matching_segments = []
    for segment in segments:
        text = segment['text'].lower()
        for keyword in prompt_keywords.get(prompt, []):
            if keyword in text:
                matching_segments.append(segment)
                break
        if len(matching_segments) >= 3:
            break

    # Fallback: match prompt words
    if not matching_segments:
        prompt_words = prompt.split()
        for segment in segments:
            if any(word in segment['text'].lower() for word in prompt_words):
                matching_segments.append(segment)
            if len(matching_segments) >= 3:
                break

    # Fallback: use first 3 segments
    if not matching_segments:
        matching_segments = segments[:3]

    # Generate GIFs with captions
    gif_paths = []
    for i, seg in enumerate(matching_segments):
        start, end = seg['start'], seg['end']
        caption = seg['text']

        clip = VideoFileClip(video_path).subclip(start, end)
        text_clip = TextClip(caption, fontsize=24, color='white', bg_color='black', size=clip.size)
        text_clip = text_clip.set_duration(clip.duration).set_position(('center', 'bottom'))

        final = CompositeVideoClip([clip, text_clip])
        gif_filename = f"gif_{i+1}.gif"
        gif_path = os.path.join(app.config['OUTPUT_FOLDER'], gif_filename)
        final.write_gif(gif_path)

        gif_paths.append(f"/output/{gif_filename}")

    return jsonify({"message": "GIFs generated successfully!", "gifs": gif_paths})

@app.route('/output/<filename>')
def serve_output_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
