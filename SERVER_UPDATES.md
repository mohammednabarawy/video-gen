# Server Startup & Logging Updates

## ✅ **Enhanced Server Startup Experience**

I've updated the application to give users full control over the ComfyUI server startup process with real-time feedback.

### 🚀 **Key Improvements**

1.  **Non-Blocking Startup**:
    - The app now launches the main window immediately.
    - Server configuration happens in the **Settings Dialog** (Connection tab).
    - No more blocking startup dialogs.

2.  **Real-Time Log Streaming**:
    - Added a **Server Logs** section to the Settings > Connection tab.
    - When you click "Start Server", logs stream in **real-time**.
    - You can see exactly what ComfyUI is doing (loading nodes, checking models, etc.).

3.  **Unified Configuration**:
    - "Configure Server" menu item now opens the main Settings dialog.
    - All server controls (Start/Stop/Logs) are in one place.

### 🔧 **Technical Changes**

- **`src/models/comfyui_server.py`**: Added `_stream_logs` method and threaded log capture.
- **`src/gui/dialogs/settings_dialog.py`**: Added log display text area and signal handling for log updates.
- **`src/main.py`**: Removed mandatory server check from startup sequence.
- **`src/gui/main_window.py`**: Updated menu actions to use the unified Settings dialog.

### 📝 **How to Test**

1.  Run the app: `python src/main.py`
2.  Go to **Edit → Configure Server...**
3.  Click **Start Server**.
4.  Watch the **Server Logs** panel expand and show real-time output from ComfyUI.
