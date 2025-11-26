"""
ComfyUI Server Manager

Manages starting, stopping, and monitoring a ComfyUI server instance.
"""

import subprocess
import time
import logging
import requests
from pathlib import Path
from typing import Optional, Callable
import psutil
import signal
import threading
import queue

logger = logging.getLogger(__name__)


class ComfyUIServer:
    """Manages ComfyUI server process"""
    
    def __init__(self, comfyui_path: str, port: int = 8188):
        """
        Initialize ComfyUI server manager
        
        Args:
            comfyui_path: Path to ComfyUI installation
            port: Port to run server on (default: 8188)
        """
        self.comfyui_path = Path(comfyui_path)
        self.port = port
        self.server_url = f"http://127.0.0.1:{port}"
        self.process: Optional[subprocess.Popen] = None
        self.log_queue = queue.Queue()
        self.log_thread = None
        self.stop_logging = threading.Event()
        
    def validate_installation(self) -> tuple[bool, str]:
        """
        Validate that ComfyUI installation is correct
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not self.comfyui_path.exists():
            return False, f"Path does not exist: {self.comfyui_path}"
        
        if not self.comfyui_path.is_dir():
            return False, f"Path is not a directory: {self.comfyui_path}"
        
        # Check for main.py
        main_py = self.comfyui_path / "main.py"
        if not main_py.exists():
            return False, f"main.py not found in {self.comfyui_path}"
        
        # Check for models directory
        models_dir = self.comfyui_path / "models"
        if not models_dir.exists():
            return False, f"models directory not found in {self.comfyui_path}"
        
        return True, "ComfyUI installation is valid"
    
    def is_running(self) -> bool:
        """
        Check if ComfyUI server is running
        
        Returns:
            True if server is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start(self, timeout: int = 30, log_callback: Optional[Callable[[str], None]] = None) -> tuple[bool, str]:
        """
        Start ComfyUI server
        
        Args:
            timeout: Maximum time to wait for server to start (seconds)
            log_callback: Optional callback function to receive log lines
            
        Returns:
            Tuple of (success, message)
        """
        # Check if already running
        if self.is_running():
            return True, "Server is already running"
        
        # Validate installation
        is_valid, message = self.validate_installation()
        if not is_valid:
            return False, f"Invalid installation: {message}"
        
        try:
            # Start server process
            logger.info(f"Starting ComfyUI server from {self.comfyui_path}")
            
            # Determine correct python executable
            import sys
            python_exe = sys.executable
            
            # Check for portable installation (python_embeded)
            # Standard portable layout: ComfyUI_windows_portable/ComfyUI/main.py
            #                           ComfyUI_windows_portable/python_embeded/python.exe
            portable_python = self.comfyui_path.parent / "python_embeded" / "python.exe"
            if portable_python.exists():
                logger.info(f"Detected portable installation, using: {portable_python}")
                python_exe = str(portable_python)
            else:
                # Check for venv
                venv_python = self.comfyui_path / "venv" / "Scripts" / "python.exe"
                if venv_python.exists():
                    logger.info(f"Detected venv, using: {venv_python}")
                    python_exe = str(venv_python)

            
            self.process = subprocess.Popen(
                [python_exe, "main.py", "--port", str(self.port)],
                cwd=str(self.comfyui_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Start log streaming thread if callback provided
            if log_callback:
                self.stop_logging.clear()
                self.log_thread = threading.Thread(
                    target=self._stream_logs,
                    args=(log_callback,),
                    daemon=True
                )
                self.log_thread.start()
            
            # Wait for server to start
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.is_running():
                    logger.info(f"ComfyUI server started successfully on port {self.port}")
                    return True, f"Server started on {self.server_url}"
                
                # Check if process died
                if self.process.poll() is not None:
                    # Read any remaining output
                    remaining_output = ""
                    if self.process.stdout:
                        remaining_output = self.process.stdout.read()
                    return False, f"Server process died: {remaining_output[:500]}"
                
                time.sleep(0.5)
            
            return False, f"Server did not start within {timeout} seconds"
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}", exc_info=True)
            return False, f"Failed to start server: {str(e)}"
    
    def stop(self) -> tuple[bool, str]:
        """
        Stop ComfyUI server
        
        Returns:
            Tuple of (success, message)
        """
        if self.process is None:
            # Check if a server is running but not managed by us
            if self.is_running():
                return False, "Server is running but was not started by this application. Please stop it manually or restart the application to manage it."
            return True, "Server was not started by this manager"
        
        try:
            # Stop log streaming
            if self.log_thread:
                self.stop_logging.set()
            
            # Try graceful shutdown first
            if self.process.poll() is None:
                self.process.terminate()
                
                # Wait up to 5 seconds for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                    logger.info("Server stopped gracefully")
                    return True, "Server stopped"
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    self.process.kill()
                    self.process.wait()
                    logger.warning("Server was force-killed")
                    return True, "Server force-stopped"
            else:
                return True, "Server was already stopped"
                
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False, f"Error stopping server: {str(e)}"
    
    def get_status(self) -> dict:
        """
        Get current server status
        
        Returns:
            Dictionary with status information
        """
        is_running = self.is_running()
        
        status = {
            'running': is_running,
            'url': self.server_url if is_running else None,
            'port': self.port,
            'path': str(self.comfyui_path)
        }
        
        if is_running:
            try:
                response = requests.get(f"{self.server_url}/system_stats", timeout=2)
                if response.status_code == 200:
                    stats = response.json()
                    status['stats'] = stats
            except:
                pass
        
        return status
    
    def _stream_logs(self, callback: Callable[[str], None]):
        """
        Stream logs from server process to callback
        
        Args:
            callback: Function to call with each log line
        """
        if not self.process or not self.process.stdout:
            return
        
        try:
            for line in iter(self.process.stdout.readline, ''):
                if self.stop_logging.is_set():
                    break
                if line:
                    callback(line.rstrip())
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                pass
