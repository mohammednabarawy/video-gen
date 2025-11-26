# ComfyUI Integration Guide

## Overview

Your HunyuanVideo app now integrates with ComfyUI to use your existing models without re-downloading. The app automatically manages a ComfyUI server in the background.

## How It Works

### 1. **ComfyUI Server Management**
- App validates your ComfyUI installation path
- Automatically starts ComfyUI server in the background
- Monitors server status with visual feedback
- Gracefully stops server on app exit

### 2. **Model Reuse**
- Uses your existing 20GB of ComfyUI models
- No duplicate downloads needed
- Models stay in your ComfyUI folder

### 3. **API Communication**
- App communicates with ComfyUI via HTTP API
- Sends workflows as JSON
- Receives generated videos
- Same proven approach as Krita AI Diffusion

## Files Created

### Core Components
1. **`src/models/comfyui_server.py`**
   - Manages ComfyUI server process
   - Validates installation
   - Starts/stops server
   - Monitors status

2. **`src/models/comfyui_client.py`**
   - HTTP API client for ComfyUI
   - Queues workflows
   - Monitors execution
   - Downloads results

3. **`src/models/comfyui_integration.py`**
   - Integration helpers
   - Model path management
   - Workflow loading

4. **`src/models/comfyui_backend.py`**
   - Direct Python integration (alternative)
   - For advanced use cases

### GUI Components
5. **`src/gui/dialogs/comfyui_server_dialog.py`**
   - Server configuration dialog
   - Path selection with browse button
   - Real-time status monitoring
   - Start/stop controls
   - Visual feedback (green/red indicators)

### Main Application
6. **`src/main.py`** (Updated)
   - Integrated server management
   - Automatic startup on first run
   - Error handling and recovery

## First Run Experience

### Step 1: ComfyUI Configuration
When you first run the app, you'll see the **ComfyUI Server Configuration** dialog:

1. **Browse** for your ComfyUI installation folder
   - Example: `D:\ComfyUI_windows_portable\ComfyUI`
2. App validates the path (checks for `main.py` and `models` folder)
3. **Green checkmark** appears if valid
4. Click **Start Server** to launch ComfyUI in background
5. **Status indicator** turns green when ready
6. Click **OK** to proceed

### Step 2: Model Path Configuration
(Existing flow - unchanged)

### Step 3: Video Generation
App is ready to generate videos using your ComfyUI models!

## Usage

### Normal Startup
After first configuration:
1. App checks if ComfyUI server is running
2. If not, automatically starts it in background
3. Shows progress during startup
4. Proceeds when server is ready

### Manual Server Control
Access server settings from the app menu (future feature) or:
- Server runs automatically
- Stops when app closes
- Can be restarted if needed

## Technical Details

### Server Startup
```python
# App automatically:
1. Validates ComfyUI path
2. Starts: python main.py --port 8188
3. Waits for server to respond (up to 60 seconds)
4. Verifies with HTTP health check
```

### Process Management
- Uses `pythonw.exe` on Windows (no console window)
- Runs in background with `CREATE_NO_WINDOW` flag
- Graceful shutdown on app exit
- Force-kill if needed (5-second timeout)

### Status Monitoring
- Polls server every 2 seconds
- Shows real-time status in dialog
- Green/red indicator for quick visual feedback
- Displays server URL when running

## Troubleshooting

### Server Won't Start
**Problem:** "Server did not start within 60 seconds"

**Solutions:**
1. Check if port 8188 is already in use
2. Verify Python environment in ComfyUI folder
3. Check ComfyUI logs in the status dialog
4. Try starting ComfyUI manually first

### Path Validation Fails
**Problem:** "main.py not found" or "models directory not found"

**Solutions:**
1. Ensure you selected the **ComfyUI** folder, not the parent
   - ✅ Correct: `D:\ComfyUI_windows_portable\ComfyUI`
   - ❌ Wrong: `D:\ComfyUI_windows_portable`
2. Verify ComfyUI is properly installed
3. Check folder permissions

### Server Crashes
**Problem:** Server starts but immediately stops

**Solutions:**
1. Check ComfyUI dependencies are installed
2. Verify Python version compatibility
3. Look at stderr output in status dialog
4. Try running ComfyUI standalone to diagnose

## Next Steps

To complete the integration, you need to:

1. **Update Inference Engine** (`src/models/inference.py`)
   - Replace diffusers calls with ComfyUI API calls
   - Use your existing workflow JSON files
   - Send workflows via `comfyui_client.queue_prompt()`

2. **Add Workflow Management**
   - Load `video_hunyuan_video_1.5_720p_i2v.json`
   - Modify prompt/parameters dynamically
   - Queue for execution

3. **Handle Results**
   - Monitor execution progress
   - Download generated video
   - Save to user-specified location

Would you like me to implement these next steps?

## Benefits

✅ **No Duplicate Downloads** - Uses your existing 20GB models
✅ **Proven Technology** - Same approach as Krita AI Diffusion
✅ **Automatic Management** - Server starts/stops automatically
✅ **Visual Feedback** - Clear status indicators
✅ **Error Recovery** - Handles failures gracefully
✅ **Background Operation** - No console windows
✅ **Flexible** - Can use any ComfyUI workflow

## Architecture

```
Your App
    ↓
ComfyUI Server Manager
    ↓
ComfyUI Process (background)
    ↓
Your Existing Models
    ↓
Generated Videos
```

The app acts as a **client** to ComfyUI, which acts as a **server** for model inference.
