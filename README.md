# 🎬 AI-Powered Video to GIF Generator

An intelligent web application that transforms videos into captioned GIFs using AI-powered content analysis. The app can process both uploaded video files and YouTube URLs, automatically extracting the most relevant segments based on user prompts.

## ✨ Features

- **🎥 Dual Input Sources**: Upload video files or provide YouTube URLs
- **🤖 AI Content Analysis**: Uses Gemini AI to intelligently select video segments based on prompts
- **📝 Automatic Captioning**: Adds text overlays to GIFs with speech transcription
- **🎯 Smart Segmentation**: Filters segments by duration (2-10 seconds) and content relevance
- **📱 Modern UI**: Beautiful, responsive web interface with drag-and-drop support
- **🎮 Interactive Experience**: Built-in Snake game to keep users entertained during processing
- **⚡ Real-time Progress**: Live progress tracking with detailed status updates
- **🔄 Batch Processing**: Generates multiple GIFs from a single video
- **💾 Automatic Cleanup**: Removes temporary files to save storage space

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **AI/ML**: OpenAI Whisper (speech recognition), Google Gemini AI (content analysis)
- **Video Processing**: MoviePy, FFmpeg
- **YouTube Integration**: yt-dlp
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Image Processing**: ImageMagick

## 📋 Prerequisites

- Python 3.8+
- FFmpeg
- ImageMagick
- Google Gemini API key
- (Optional) OpenAI API key

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd gif
```

### 2. Install System Dependencies

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg imagemagick ttf-dejavu
```

**On Windows:**
- Download and install [FFmpeg](https://ffmpeg.org/download.html)
- Download and install [ImageMagick](https://imagemagick.org/script/download.php#windows)
- Update the ImageMagick path in `app.py` if needed

**On macOS:**
```bash
brew install ffmpeg imagemagick
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

Edit `app.py` and set your API keys:

```python
# Google Gemini API (required)
genai.configure(api_key='YOUR_GEMINI_API_KEY')

# OpenAI API (optional, for enhanced features)
openai.api_key = 'YOUR_OPENAI_API_KEY'
```

### 5. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📖 Usage

### 1. Web Interface
1. Open your browser and navigate to `http://localhost:5000`
2. Enter a theme/prompt describing what type of content you want to extract
3. Choose your input method:
   - **YouTube URL**: Paste a YouTube link for quick processing
   - **File Upload**: Drag and drop or select a video file
4. Click "Generate GIFs" and wait for processing
5. Download your generated GIFs

### 2. Example Prompts
- "funny moments"
- "emotional quotes"
- "action scenes"
- "motivational clips"
- "dramatic dialogue"

### 3. Supported Video Formats
- MP4, AVI, MOV, MKV, WEBM
- Maximum duration: 10 minutes for uploads, 15 minutes for YouTube videos
- Maximum file size: 100MB

## 🔧 Configuration

### Environment Variables
You can set API keys as environment variables:
```bash
export GEMINI_API_KEY="your_gemini_api_key"
export OPENAI_API_KEY="your_openai_api_key"
```

### Custom Settings
Modify `app.py` to adjust:
- Maximum file size (`MAX_CONTENT_LENGTH`)
- Video duration limits
- GIF quality settings
- ImageMagick path (Windows)

## 📁 Project Structure

```
gif/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── build.sh              # Build script for deployment
├── templates/
│   └── index.html        # Web interface
├── static/               # Static assets (CSS, JS)
├── uploads/              # Temporary uploaded files
├── output/               # Generated GIFs
└── README.md            # This file
```

## 🔄 API Endpoints

- `GET /` - Main web interface
- `POST /generate` - Start GIF generation process
- `GET /progress/<job_id>` - Check processing progress
- `GET /download/<filename>` - Download generated GIF
- `POST /cleanup` - Clean up temporary files

## 🤖 AI Processing Pipeline

1. **Input Validation**: Checks file format and duration limits
2. **Speech Recognition**: Uses Whisper to transcribe audio
3. **Content Analysis**: Gemini AI analyzes transcript segments
4. **Segment Selection**: Filters and ranks segments based on prompt
5. **Video Processing**: Downloads/processes selected segments
6. **GIF Generation**: Creates captioned GIFs with text overlays
7. **Cleanup**: Removes temporary files

## 🎮 Interactive Features

- **Snake Game**: Play while your video processes
- **Real-time Progress**: Live updates on processing status
- **Drag & Drop**: Easy file upload interface
- **Responsive Design**: Works on desktop and mobile devices

## 🔒 Security & Performance

- File type validation
- Size limits enforcement
- Automatic cleanup of temporary files
- Threaded processing for non-blocking operations
- Error handling and user feedback

## 🐛 Troubleshooting

### Common Issues

1. **ImageMagick not found**
   - Ensure ImageMagick is installed and the path is correct in `app.py`
   - Windows users may need to update the path: `r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"`

2. **FFmpeg not found**
   - Install FFmpeg and ensure it's in your system PATH

3. **API key errors**
   - Verify your Gemini API key is correctly set
   - Check API quota limits

4. **Memory issues with large videos**
   - Reduce video quality or duration
   - Ensure sufficient system memory

### Debug Mode
Run with debug enabled for detailed error messages:
```python
app.run(debug=True, port=5000)
```
## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review the code comments
- Open an issue on GitHub

## 🔮 Future Enhancements

- [ ] Support for more video formats
- [ ] Custom GIF styling options
- [ ] Batch processing for multiple videos
- [ ] Social media integration
- [ ] Advanced AI models for better content selection
- [ ] User accounts and history
- [ ] API rate limiting and optimization

---

**Made with ❤️ using AI and modern web technologies** 