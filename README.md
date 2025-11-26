# HunyuanVideo 1.5 Video Generator

A cross-platform desktop application for generating high-quality videos using Tencent's HunyuanVideo 1.5 model. Supports both Text-to-Video (T2V) and Image-to-Video (I2V) generation with an intuitive GUI.

## Features

- 🎬 **Text-to-Video Generation**: Create videos from text descriptions
- 🖼️ **Image-to-Video Generation**: Animate static images
- 🔄 **ComfyUI Compatible**: Reuse existing ComfyUI models to avoid duplicate downloads
- 🎨 **Style Presets**: Cinematic, Realistic, Anime, 3D, and Artistic styles
- 📹 **Camera Controls**: Pan, zoom, tilt, orbit, and more
- ⚙️ **Advanced Options**: CFG scale, inference steps, super-resolution upscaling
- 💾 **Smart Model Management**: Automatic detection and download of required models
- 🖥️ **GPU Optimized**: Automatic VRAM management and CPU offloading

## Requirements

### Hardware
- **GPU**: NVIDIA GPU with CUDA support
- **VRAM**: Minimum 14GB (24GB+ recommended for best performance)
- **Storage**: ~25-30GB for model files
- **RAM**: 16GB+ recommended

### Software
- Windows 10/11, Linux, or macOS (with CUDA support)
- Python 3.10 or higher
- CUDA Toolkit 11.8+ (for GPU acceleration)

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install PyTorch with CUDA** (if not already installed):
```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Usage

### First Run

1. **Launch the application**:
```bash
python src/main.py
```

2. **Model Setup**:
   - On first run, the app will check for existing models
   - If you have ComfyUI installed, it will auto-detect and offer to use your existing models
   - Otherwise, you can download models to a custom location or the default cache

3. **Model Download**:
   - Required models (~25GB) will be downloaded automatically
   - Progress will be shown in the setup dialog
   - This is a one-time process

### Generating Videos

1. **Choose Mode**: Text-to-Video or Image-to-Video
2. **Enter Prompt**: Describe the video you want to generate
3. **Adjust Settings**:
   - Resolution: 480p, 720p, or 1080p (with super-resolution)
   - Duration: 2-10 seconds
   - Style: Choose from presets or customize
   - Camera Motion: Static, zoom, pan, etc.
4. **Generate**: Click "Generate Video" and wait for processing
5. **Preview & Save**: Preview the generated video and save to your desired location

### Example Prompts

- "A golden retriever running on a beach at sunset, cinematic, 4K quality"
- "Abstract colorful geometric shapes morphing, 3D render, smooth animation"
- "Anime girl with flowing hair in the wind, Studio Ghibli style, detailed"
- "Drone shot flying over a misty mountain valley, epic landscape"

## ComfyUI Integration

If you already have ComfyUI with HunyuanVideo models:

1. The app will auto-detect ComfyUI in common locations:
   - `C:/ComfyUI/models`
   - `~/ComfyUI/models`
   - Or browse to your custom location

2. Point the app to your ComfyUI models folder in Settings

3. The app will use existing models and only download what's missing

## Configuration

Settings are stored in:
- **Windows**: `C:\Users\<username>\.hunyuanvideo\config.yaml`
- **Linux/Mac**: `~/.hunyuanvideo/config.yaml`

You can edit this file to customize default settings, paths, and preferences.

## Troubleshooting

### Out of Memory Errors
- Enable "CPU Offloading" in Advanced Options
- Enable "VAE Tiling" for high resolutions
- Reduce resolution or duration
- Close other GPU-intensive applications

### Slow Generation
- Ensure GPU drivers are up to date
- Check that CUDA is properly installed
- Consider using distilled models (4-step inference)
- Verify models are on SSD, not HDD

### Model Download Issues
- Check internet connection
- Ensure sufficient disk space
- Try downloading models manually from HuggingFace

## License

This application is a GUI wrapper for HunyuanVideo 1.5 by Tencent. Please refer to the original model's license and terms of use.

## Credits

- **HunyuanVideo Model**: Tencent Hunyuan Team
- **Diffusers Library**: Hugging Face
- **GUI Framework**: PyQt6

## Support

For issues and questions:
1. Check the logs in `~/.hunyuanvideo/logs/`
2. Review the troubleshooting section
3. Open an issue on GitHub (if applicable)

---

**Note**: This is an unofficial community tool. For official model information, visit:
- https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
- https://huggingface.co/tencent/HunyuanVideo
