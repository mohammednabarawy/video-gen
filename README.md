# HunyuanVideo 1.5 Generator

<div align="center">

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

**A professional desktop application for generating high-quality AI videos using Tencent's HunyuanVideo 1.5 model**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Documentation](#-documentation) • [Troubleshooting](#-troubleshooting)

</div>

---

## 🎬 Overview

HunyuanVideo Generator is a cross-platform desktop application that provides an intuitive GUI for Tencent's state-of-the-art HunyuanVideo 1.5 model. Generate stunning videos from text descriptions or animate static images with advanced controls and real-time previews.

### Why HunyuanVideo Generator?

- **🚀 Easy to Use**: No command-line expertise required - intuitive GUI for all features
- **🔄 ComfyUI Integration**: Seamlessly integrates with existing ComfyUI installations to avoid duplicate model downloads
- **⚡ Optimized Performance**: Automatic VRAM management, FP8 quantization, and Low VRAM mode for 12-16GB GPUs
- **🎨 Professional Controls**: Style presets, camera motions, and advanced generation parameters
- **� Smart Model Management**: Automatic model detection, download, and caching

## ✨ Features

### Core Capabilities
- **Text-to-Video (T2V)**: Generate videos from detailed text descriptions
- **Image-to-Video (I2V)**: Animate static images with motion and camera controls
- **Real-Time Preview**: Watch generation progress with live frame previews
- **Batch Processing**: Queue multiple generations with preset library

### Advanced Features
- **🎨 Style Presets**: Cinematic, Realistic, Anime, 3D, Artistic, and more
- **📹 Camera Controls**: Pan, zoom, tilt, orbit, dolly, and custom camera paths
- **⚙️ Performance Modes**: AUTO, LOW, MEDIUM, HIGH presets for different VRAM levels
- **🔧 Advanced Options**: 
  - CFG scale control (1.0-20.0)
  - Inference steps (10-100)
  - Super-resolution upscaling
  - VAE tiling for memory efficiency
  - CPU offloading for low VRAM systems
  - Prompt rewriting with LLM enhancement

### Technical Features
- **ComfyUI Backend**: Leverages ComfyUI's powerful workflow system
- **FP8 Quantization**: Automatic FP8 weight loading for Low VRAM mode
- **Automated Node Management**: Auto-installs required ComfyUI custom nodes
- **Server Management**: Automatic ComfyUI server startup/shutdown
- **Error Recovery**: Intelligent retry logic with memory optimizations

## 📋 Requirements

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **GPU** | NVIDIA GPU with 12GB VRAM | RTX 4090 (24GB VRAM) | CUDA support required |
| **VRAM** | 12GB | 24GB+ | 480p @ 12GB, 720p @ 16GB+, 1080p @ 24GB+ |
| **Storage** | 30GB free | 50GB+ SSD | For models and cache |
| **RAM** | 16GB | 32GB+ | System memory |
| **CPU** | 4 cores | 8+ cores | For offloading |

### VRAM Guidelines

| VRAM | Max Resolution | Max Duration | Recommended Settings |
|------|----------------|--------------|---------------------|
| 12GB | 480p (854x480) | 2 seconds (49 frames) | LOW preset, FP8, VAE tiling |
| 16GB | 720p (1280x720) | 3 seconds (73 frames) | MEDIUM preset, FP8 |
| 24GB+ | 1080p (1920x1080) | 5 seconds (125 frames) | HIGH preset, FP16 |

### Software Requirements
- **OS**: Windows 10/11, Linux (Ubuntu 20.04+), or macOS (with CUDA support)
- **Python**: 3.10 or higher
- **CUDA**: 11.8+ or 12.1+ (for GPU acceleration)
- **ComfyUI**: Optional (auto-installed if not present)

## 🚀 Installation

### Quick Start (Windows)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mohammednabarawy/video-gen.git
   cd video-gen
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install PyTorch with CUDA**:
   ```bash
   # For CUDA 11.8
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # For CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

5. **Launch the application**:
   ```bash
   python src/main.py
   ```

### Linux/macOS Installation

```bash
# Clone repository
git clone https://github.com/mohammednabarawy/video-gen.git
cd video-gen

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Launch
python src/main.py
```

### ComfyUI Integration (Optional)

If you already have ComfyUI installed:

1. The app will auto-detect ComfyUI in common locations:
   - Windows: `C:\ComfyUI_windows_portable\ComfyUI`
   - Linux/Mac: `~/ComfyUI`

2. Or manually configure in Settings → Server → ComfyUI Path

3. The app will use your existing models and only download what's missing

## 📖 Usage

### First Run Setup

1. **Launch the application**:
   ```bash
   python src/main.py
   ```

2. **Initial Configuration**:
   - The setup dialog will guide you through configuration
   - Choose your ComfyUI installation path (or let it auto-install)
   - Select performance preset based on your VRAM
   - Models will be downloaded automatically (~25-30GB)

3. **Model Download**:
   - Required models are downloaded from HuggingFace
   - Progress is shown in real-time
   - This is a one-time process (unless you change model paths)

### Generating Your First Video

#### Text-to-Video

1. **Select Mode**: Choose "Text-to-Video" tab
2. **Enter Prompt**: 
   ```
   A golden retriever running on a beach at sunset, 
   cinematic composition, dramatic lighting, 4K quality
   ```
3. **Configure Settings**:
   - **Resolution**: 720p (for 16GB VRAM)
   - **Duration**: 3 seconds
   - **FPS**: 24
   - **Style**: Cinematic
   - **Camera Motion**: Pan Right
4. **Advanced Options**:
   - **CFG Scale**: 7.0
   - **Inference Steps**: 20
   - **Enable VAE Tiling**: ✓
   - **Enable CPU Offload**: ✓ (for <24GB VRAM)
5. **Generate**: Click "Generate Video"
6. **Preview**: Watch real-time generation progress
7. **Save**: Export to your desired location

#### Image-to-Video

1. **Select Mode**: Choose "Image-to-Video" tab
2. **Load Image**: Click "Browse" and select your image
3. **Enter Prompt**: Describe the desired motion
   ```
   Camera slowly zooming in, gentle wind blowing, 
   cinematic atmosphere
   ```
4. **Configure Settings**: Same as T2V
5. **Generate**: Process and preview

### Example Prompts

**Cinematic**:
```
Aerial drone shot flying over a misty mountain valley at dawn, 
epic landscape, volumetric fog, golden hour lighting, 
cinematic composition, 4K quality
```

**Anime**:
```
Anime girl with flowing pink hair in the wind, 
cherry blossoms falling, Studio Ghibli style, 
detailed animation, soft lighting, dreamy atmosphere
```

**Abstract**:
```
Abstract colorful geometric shapes morphing and transforming, 
3D render, smooth animation, vibrant colors, 
psychedelic patterns, seamless loop
```

**Realistic**:
```
Close-up of coffee being poured into a white ceramic cup, 
steam rising, macro photography, shallow depth of field, 
warm lighting, photorealistic, slow motion
```

## 🎨 Performance Presets

The app includes automatic performance presets based on your VRAM:

| Preset | VRAM | Resolution | Max Frames | Features |
|--------|------|------------|------------|----------|
| **LOW** | 12GB | 480p | 49 (2 sec) | FP8, VAE tiling, CPU offload |
| **MEDIUM** | 16GB | 720p | 73 (3 sec) | FP8, VAE tiling |
| **HIGH** | 24GB+ | 1080p | 125 (5 sec) | FP16, no tiling |
| **AUTO** | Any | Auto-detect | Auto-detect | Automatic optimization |

## 📚 Documentation

- **[Setup Guide](SETUP.md)**: Detailed installation and configuration
- **[ComfyUI Integration](COMFYUI_INTEGRATION.md)**: ComfyUI setup and workflow details
- **[Settings System](SETTINGS_SYSTEM.md)**: Configuration options and customization
- **[Server Updates](SERVER_UPDATES.md)**: Server management and troubleshooting

## 🔧 Configuration

### Settings Location

Settings are stored in JSON format:
- **Windows**: `%APPDATA%\HunyuanVideoGenerator\settings.json`
- **Linux/Mac**: `~/.config/HunyuanVideoGenerator/settings.json`

### Key Configuration Options

```json
{
  "server_mode": "LOCAL",
  "comfyui_path": "D:/ComfyUI_windows_portable/ComfyUI",
  "performance_preset": "AUTO",
  "default_resolution": "720p",
  "default_inference_steps": 20,
  "enable_vae_tiling": true,
  "enable_cpu_offload": true
}
```

## 🐛 Troubleshooting

### Out of Memory (OOM) Errors

**Problem**: `torch.OutOfMemoryError: Allocation on device`

**Solutions**:
1. **Reduce Resolution**: Use 480p instead of 720p
2. **Reduce Duration**: Generate 2-3 seconds instead of 5
3. **Enable Optimizations**:
   - ✓ Enable VAE Tiling
   - ✓ Enable CPU Offload
   - ✓ Use LOW performance preset
4. **Reduce Steps**: Use 10-20 steps instead of 50
5. **Close Other Apps**: Free up VRAM by closing browsers, games, etc.

### Slow Generation

**Problem**: Generation takes too long

**Solutions**:
1. **Update GPU Drivers**: Ensure latest NVIDIA drivers
2. **Verify CUDA**: Check `torch.cuda.is_available()` returns `True`
3. **Use SSD**: Move models to SSD instead of HDD
4. **Reduce Quality**: Lower resolution or steps
5. **Check CPU Usage**: Ensure CPU offload isn't bottlenecking

### ComfyUI Server Issues

**Problem**: Server fails to start or crashes

**Solutions**:
1. **Manual Start**: Start ComfyUI manually with `--lowvram` flag:
   ```bash
   cd D:\ComfyUI_windows_portable\ComfyUI
   ..\python_embeded\python.exe main.py --port 8188 --lowvram
   ```
2. **Check Ports**: Ensure port 8188 is not in use
3. **Review Logs**: Check ComfyUI logs for errors
4. **Reinstall Nodes**: Delete and reinstall custom nodes

### Model Download Issues

**Problem**: Models fail to download

**Solutions**:
1. **Check Internet**: Verify stable connection
2. **Free Space**: Ensure 30GB+ free disk space
3. **Manual Download**: Download from [HuggingFace](https://huggingface.co/tencent/HunyuanVideo) manually
4. **Proxy Settings**: Configure proxy if behind firewall

### Windows-Specific Issues

**Problem**: `[Errno 22] Invalid argument` in ComfyUI logs

**Solution**: This is a known Windows logging bug in ComfyUI. It's harmless but can be avoided by:
1. Starting ComfyUI manually (see above)
2. Letting the app connect to the running server
3. Not using the app's automatic server management

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

```bash
# Clone repository
git clone https://github.com/mohammednabarawy/video-gen.git
cd video-gen

# Create development environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python src/main.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note**: This application is a GUI wrapper for HunyuanVideo 1.5 by Tencent. The underlying model has its own license and terms of use. Please refer to:
- [HunyuanVideo Official Repository](https://github.com/Tencent-Hunyuan/HunyuanVideo)
- [HuggingFace Model Card](https://huggingface.co/tencent/HunyuanVideo)

## 🙏 Credits

- **HunyuanVideo Model**: [Tencent Hunyuan Team](https://github.com/Tencent-Hunyuan/HunyuanVideo)
- **ComfyUI**: [ComfyUI Project](https://github.com/comfyanonymous/ComfyUI)
- **Diffusers Library**: [Hugging Face](https://github.com/huggingface/diffusers)
- **GUI Framework**: [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)

## 📞 Support

For issues, questions, or feature requests:

1. **Check Documentation**: Review the docs in this repository
2. **Search Issues**: Look for similar issues on GitHub
3. **Open an Issue**: Create a new issue with detailed information
4. **Community**: Join discussions in the Issues section

## 🗺️ Roadmap

- [ ] **Multi-GPU Support**: Distribute generation across multiple GPUs
- [ ] **Batch Processing**: Queue and process multiple videos
- [ ] **Video Editing**: Trim, merge, and edit generated videos
- [ ] **Cloud Integration**: Optional cloud generation for users without GPUs
- [ ] **Plugin System**: Extensible architecture for community plugins
- [ ] **LoRA Support**: Fine-tuned model support
- [ ] **Advanced Scheduling**: Custom noise schedulers and samplers

## ⭐ Star History

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

<div align="center">

**Made with ❤️ by the community**

[Report Bug](https://github.com/mohammednabarawy/video-gen/issues) • [Request Feature](https://github.com/mohammednabarawy/video-gen/issues) • [Documentation](https://github.com/mohammednabarawy/video-gen/wiki)

</div>
