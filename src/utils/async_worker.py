"""Async worker for non-blocking video generation"""

from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class VideoGenerationWorker(QThread):
    """Worker thread for video generation"""
    
    # Signals
    progress_updated = pyqtSignal(int, int, str)  # step, total_steps, status
    generation_complete = pyqtSignal(object)  # video_frames (numpy array)
    generation_failed = pyqtSignal(str)  # error_message
    
    def __init__(
        self,
        inference_engine,
        prompt: str,
        params: Dict[str, Any],
        parent=None
    ):
        """
        Initialize worker
        
        Args:
            inference_engine: HunyuanVideoInference instance
            prompt: Text prompt
            params: Generation parameters dictionary
            parent: Parent QObject
        """
        super().__init__(parent)
        self.inference_engine = inference_engine
        self.prompt = prompt
        self.params = params
        self._is_cancelled = False
    
    def cancel(self):
        """Cancel the generation"""
        self._is_cancelled = True
        logger.info("Generation cancelled by user")
    
    def _progress_callback(self, step: int, total_steps: int, latency: float):
        """Progress callback for inference"""
        if self._is_cancelled:
            raise InterruptedError("Generation cancelled")
        
        status = f"Generating frame {step}/{total_steps}..."
        self.progress_updated.emit(step, total_steps, status)
    
    def run(self):
        """Run the generation task"""
        try:
            logger.info("Worker started")
            self.progress_updated.emit(0, 100, "Initializing...")
            
            # Add progress callback to params
            self.params['progress_callback'] = self._progress_callback
            
            # Generate video
            video_frames = self.inference_engine.generate_video(
                prompt=self.prompt,
                **self.params
            )
            
            if video_frames is not None:
                self.generation_complete.emit(video_frames)
            else:
                self.generation_failed.emit("Generation failed - no output produced")
                
        except InterruptedError:
            self.generation_failed.emit("Generation cancelled by user")
        except Exception as e:
            error_msg = f"Error during generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.generation_failed.emit(error_msg)


class ModelDownloadWorker(QThread):
    """Worker thread for model downloading"""
    
    # Signals
    download_progress = pyqtSignal(str, float)  # filename, progress_percent
    download_complete = pyqtSignal(bool)  # success
    download_failed = pyqtSignal(str)  # error_message
    status_updated = pyqtSignal(str)  # status_message
    
    def __init__(
        self,
        downloader,
        include_optional: bool = False,
        parent=None
    ):
        """
        Initialize worker
        
        Args:
            downloader: ModelDownloader instance
            include_optional: Whether to download optional models
            parent: Parent QObject
        """
        super().__init__(parent)
        self.downloader = downloader
        self.include_optional = include_optional
    
    def _progress_callback(self, filename: str, progress: float):
        """Progress callback for downloads"""
        self.download_progress.emit(filename, progress)
    
    def run(self):
        """Run the download task"""
        try:
            logger.info("Download worker started")
            self.status_updated.emit("Checking existing models...")
            
            # Set progress callback
            self.downloader.progress_callback = self._progress_callback
            
            # Download models
            success = self.downloader.download_all_models(
                include_optional=self.include_optional
            )
            
            if success:
                self.status_updated.emit("All models downloaded successfully!")
                self.download_complete.emit(True)
            else:
                self.download_failed.emit("Some models failed to download")
                
        except Exception as e:
            error_msg = f"Error during download: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.download_failed.emit(error_msg)
