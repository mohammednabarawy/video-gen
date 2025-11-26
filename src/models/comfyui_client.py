"""
ComfyUI API Client

This module provides a client for interacting with ComfyUI's HTTP API and WebSocket.
Based on the approach used by Krita AI Diffusion.
"""

import requests
import json
import time
import uuid
import threading
import websocket
import io
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Union
import logging

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Client for ComfyUI HTTP API and WebSocket"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8188"):
        """
        Initialize ComfyUI API client
        
        Args:
            server_url: URL of ComfyUI server
        """
        self.server_url = server_url.rstrip('/')
        self.ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        self.client_id = str(uuid.uuid4())
        
        self.ws = None
        self.ws_thread = None
        self.is_connected = False
        self.callbacks = {
            'progress': [],
            'preview': [],
            'execution_start': [],
            'execution_cached': [],
            'executing': [],
            'execution_success': [],
            'execution_error': []
        }
        
        logger.info(f"ComfyUI client initialized for {self.server_url}")
    
    def _retry_request(self, func: Callable, retries: int = 3, delay: float = 1.0) -> Any:
        """
        Retry a request function with exponential backoff
        
        Args:
            func: Function to execute
            retries: Number of retries
            delay: Initial delay in seconds
            
        Returns:
            Function result
        """
        last_exception = None
        for i in range(retries + 1):
            try:
                return func()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_exception = e
                if i < retries:
                    sleep_time = delay * (2 ** i)
                    logger.warning(f"Request failed, retrying in {sleep_time}s... ({i+1}/{retries})")
                    time.sleep(sleep_time)
            except Exception as e:
                # Don't retry other exceptions
                raise e
                
        logger.error(f"Request failed after {retries} retries: {last_exception}")
        raise last_exception

    def connect(self):
        """Connect to ComfyUI WebSocket"""
        if self.is_connected:
            return

        def on_message(ws, message):
            self._handle_message(message)

        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            self.is_connected = False

        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket connection closed")
            self.is_connected = False

        def on_open(ws):
            logger.info("WebSocket connection established")
            self.is_connected = True

        self.ws = websocket.WebSocketApp(
            f"{self.ws_url}/ws?clientId={self.client_id}",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Wait for connection
        start_time = time.time()
        while not self.is_connected and time.time() - start_time < 5:
            time.sleep(0.1)
            
    def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws:
            self.ws.close()
            self.is_connected = False
            
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback for an event type"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            
    def _handle_message(self, message):
        """Handle incoming WebSocket message"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
                msg_type = data.get('type')
                msg_data = data.get('data', {})
                
                if msg_type == 'status':
                    return
                    
                if msg_type == 'progress':
                    # {'value': 1, 'max': 20}
                    for cb in self.callbacks['progress']:
                        cb(msg_data)
                        
                elif msg_type == 'executing':
                    # {'node': '10', 'display_node': '10', 'prompt_id': '...'}
                    for cb in self.callbacks['executing']:
                        cb(msg_data)
                        
                elif msg_type == 'execution_start':
                    for cb in self.callbacks['execution_start']:
                        cb(msg_data)
                        
                elif msg_type == 'execution_cached':
                    for cb in self.callbacks['execution_cached']:
                        cb(msg_data)
                        
                elif msg_type == 'execution_success':
                    for cb in self.callbacks['execution_success']:
                        cb(msg_data)
                        
                elif msg_type == 'execution_error':
                    logger.error(f"Execution error: {msg_data}")
                    for cb in self.callbacks['execution_error']:
                        cb(msg_data)
                        
            elif isinstance(message, bytes):
                # Binary preview data
                # First 4 bytes are type (1=JPEG, 2=PNG)
                # Remaining is image data
                if len(message) > 8:
                    event_type = int.from_bytes(message[0:4], byteorder='big')
                    image_type = int.from_bytes(message[4:8], byteorder='big')
                    image_data = message[8:]
                    
                    # 1=JPEG, 2=PNG
                    format_str = "jpeg" if image_type == 1 else "png"
                    
                    for cb in self.callbacks['preview']:
                        cb(image_data, format_str)
                        
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def is_server_running(self) -> bool:
        """
        Check if ComfyUI server is running
        
        Returns:
            True if server is accessible, False otherwise
        """
        try:
            def _check():
                response = requests.get(f"{self.server_url}/system_stats", timeout=2)
                return response.status_code == 200
                
            return self._retry_request(_check, retries=1, delay=0.5)
        except:
            return False
    
    def queue_prompt(self, workflow: Dict[str, Any]) -> Optional[str]:
        """
        Queue a prompt/workflow for execution
        
        Args:
            workflow: ComfyUI workflow dictionary
            
        Returns:
            Prompt ID if successful, None otherwise
        """
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            def _queue():
                return requests.post(
                    f"{self.server_url}/prompt",
                    json=payload,
                    timeout=10
                )
            
            response = self._retry_request(_queue)
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get('prompt_id')
                logger.info(f"Queued prompt: {prompt_id}")
                return prompt_id
            else:
                logger.error(f"Failed to queue prompt: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error queuing prompt: {e}")
            return None
    
    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution history for a prompt
        
        Args:
            prompt_id: Prompt ID to check
            
        Returns:
            History data or None if not found
        """
        try:
            def _get():
                return requests.get(f"{self.server_url}/history/{prompt_id}", timeout=5)
                
            response = self._retry_request(_get, retries=2)
            
            if response.status_code == 200:
                history = response.json()
                return history.get(prompt_id)
            return None
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return None
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> bool:
        """
        Wait for a prompt to complete execution
        
        Args:
            prompt_id: Prompt ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if completed successfully, False otherwise
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)
            
            if history:
                # Check if execution is complete
                if 'outputs' in history:
                    logger.info(f"Prompt {prompt_id} completed successfully")
                    return True
                elif 'status' in history and history['status'].get('completed'):
                    logger.info(f"Prompt {prompt_id} completed")
                    return True
            
            time.sleep(1)
        
        logger.error(f"Timeout waiting for prompt {prompt_id}")
        return False
    
    def get_output_images(self, prompt_id: str) -> list:
        """
        Get output images/videos from a completed prompt
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            List of output file information
        """
        history = self.get_history(prompt_id)
        if not history or 'outputs' not in history:
            return []
        
        outputs = []
        for node_id, node_output in history['outputs'].items():
            if 'images' in node_output:
                for image in node_output['images']:
                    outputs.append({
                        'filename': image['filename'],
                        'subfolder': image.get('subfolder', ''),
                        'type': image.get('type', 'output')
                    })
            elif 'gifs' in node_output:
                for gif in node_output['gifs']:
                    outputs.append({
                        'filename': gif['filename'],
                        'subfolder': gif.get('subfolder', ''),
                        'type': 'output'
                    })
            elif 'videos' in node_output:
                for video in node_output['videos']:
                    outputs.append({
                        'filename': video['filename'],
                        'subfolder': video.get('subfolder', ''),
                        'type': video.get('type', 'output')
                    })
            elif 'VHS_FILENAMES' in node_output:
                # VHS nodes return a tuple with filenames in the second element
                # Or sometimes a list of filenames directly
                vhs_output = node_output['VHS_FILENAMES']
                if isinstance(vhs_output, list) and len(vhs_output) > 0:
                    # Check if it's a list of strings (filenames)
                    if isinstance(vhs_output[0], str):
                        for filename in vhs_output:
                            outputs.append({
                                'filename': Path(filename).name,
                                'subfolder': '', # VHS usually gives full path
                                'type': 'output'
                            })
            else:
                logger.warning(f"Unknown output format for node {node_id}: {list(node_output.keys())}")
        
        return outputs
    
    def download_output(self, filename: str, subfolder: str = '', output_type: str = 'output', save_path: Optional[str] = None) -> Optional[Path]:
        """
        Download an output file from ComfyUI
        
        Args:
            filename: Output filename
            subfolder: Subfolder in output directory
            output_type: Type of output ('output', 'temp', etc.)
            save_path: Where to save the file (if None, returns bytes)
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            params = {
                'filename': filename,
                'subfolder': subfolder,
                'type': output_type
            }
            
            response = requests.get(
                f"{self.server_url}/view",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                if save_path:
                    save_path = Path(save_path)
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Downloaded output to {save_path}")
                    return save_path
                return response.content
            else:
                logger.error(f"Failed to download output: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading output: {e}")
            return None
