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
    
    def start(self, timeout: int = 30, log_callback: Optional[Callable[[str], None]] = None, args: list[str] = None) -> tuple[bool, str]:
        """
        Start ComfyUI server
        
        Args:
            timeout: Maximum time to wait for server to start (seconds)
            log_callback: Optional callback function to receive log lines
            args: Optional list of command line arguments to pass to ComfyUI
            
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

            
            cmd = [python_exe, "main.py", "--port", str(self.port)]
            if args:
                cmd.extend(args)
                
            self.process = subprocess.Popen(
                cmd,
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
    
    def stop(self, force: bool = False) -> tuple[bool, str]:
        """
        Stop ComfyUI server with improved Windows process cleanup
        
        Args:
            force: If True, immediately kill the process without graceful shutdown
        
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
            
            # Check if process is still running
            if self.process.poll() is None:
                if force:
                    # Immediate force kill
                    logger.info("Force killing server process...")
                    self._kill_process_tree(self.process.pid)
                    return True, "Server force-stopped"
                
                # Try graceful shutdown first
                logger.info("Attempting graceful server shutdown...")
                self.process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown (increased from 5)
                try:
                    self.process.wait(timeout=10)
                    logger.info("Server stopped gracefully")
                    return True, "Server stopped"
                except subprocess.TimeoutExpired:
                    # Force kill the entire process tree
                    logger.warning("Graceful shutdown timed out, force killing process tree...")
                    self._kill_process_tree(self.process.pid)
                    return True, "Server force-stopped after timeout"
            else:
                return True, "Server was already stopped"
                
        except Exception as e:
            logger.error(f"Error stopping server: {e}", exc_info=True)
            # Try force kill as last resort
            try:
                if self.process and self.process.poll() is None:
                    self._kill_process_tree(self.process.pid)
                    return True, f"Server stopped (error occurred but recovered): {str(e)}"
            except:
                pass
            return False, f"Error stopping server: {str(e)}"
    
    def _kill_process_tree(self, pid: int):
        """
        Kill a process and all its children (Windows-safe)
        
        Args:
            pid: Process ID to kill
        """
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # Kill all children first
            for child in children:
                try:
                    logger.debug(f"Killing child process {child.pid}")
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # Kill parent
            try:
                logger.debug(f"Killing parent process {pid}")
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            
            # Wait for processes to terminate
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            
            if alive:
                logger.warning(f"{len(alive)} processes still alive after kill")
                
        except psutil.NoSuchProcess:
            logger.debug(f"Process {pid} already terminated")
        except Exception as e:
            logger.error(f"Error killing process tree: {e}", exc_info=True)
    def restart(self, timeout: int = 30, args: list[str] = None, force_stop: bool = False) -> tuple[bool, str]:
        """
        Restart ComfyUI server with improved reliability
        
        Args:
            timeout: Timeout for start operation
            args: Optional list of command line arguments
            force_stop: If True, force kill the process instead of graceful shutdown
            
        Returns:
            Tuple of (success, message)
        """
        logger.info("Restarting ComfyUI server...")
        
        # Stop existing server (with force option)
        success, message = self.stop(force=force_stop)
        if not success:
            logger.warning(f"Stop failed but continuing: {message}")
        
        # Wait longer for Windows to release file handles (increased from 2 to 5 seconds)
        logger.info("Waiting for file handles to be released...")
        time.sleep(5)
        
        # Additional wait if process tree cleanup was needed
        if force_stop or "force" in message.lower():
            logger.info("Force stop detected, waiting additional time...")
            time.sleep(3)
        
        # Clear the process reference
        self.process = None
        
        # Start new instance with retries
        max_retries = 2
        for attempt in range(max_retries):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                time.sleep(2)
            
            success, message = self.start(timeout=timeout, args=args)
            if success:
                return True, message
                
        return False, f"Server restart failed after {max_retries} attempts: {message}"
        
    def check_health(self) -> bool:
        """
        Check if server is healthy and responsive
        
        Returns:
            True if healthy
        """
        try:
            if not self.process or self.process.poll() is not None:
                return False
                
            response = requests.get(f"{self.server_url}/system_stats", timeout=1)
            return response.status_code == 200
        except:
            return False
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
