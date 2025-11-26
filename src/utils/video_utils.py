"""Video processing utilities"""

from pathlib import Path
from typing import Optional
import imageio
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class VideoUtils:
    """Utility functions for video processing"""
    
    @staticmethod
    def save_video(
        frames: np.ndarray,
        output_path: Path,
        fps: int = 25,
        codec: str = 'libx264',
        quality: int = 8
    ) -> bool:
        """
        Save video frames to file
        
        Args:
            frames: Video frames as numpy array (num_frames, height, width, channels)
            output_path: Output file path
            fps: Frames per second
            codec: Video codec
            quality: Quality setting (0-10, higher is better)
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Saving video to: {output_path}")
            logger.info(f"Shape: {frames.shape}, FPS: {fps}")
            
            writer = imageio.get_writer(
                str(output_path),
                fps=fps,
                codec=codec,
                quality=quality,
                pixelformat='yuv420p'
            )
            
            for frame in frames:
                writer.append_data(frame)
            
            writer.close()
            
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ Video saved: {output_path} ({file_size_mb:.1f} MB)")
            return True
            
        except Exception as e:
            logger.error(f"Error saving video: {e}")
            return False
    
    @staticmethod
    def extract_thumbnail(
        frames: np.ndarray,
        frame_index: Optional[int] = None
    ) -> Image.Image:
        """
        Extract a thumbnail from video frames
        
        Args:
            frames: Video frames array
            frame_index: Index of frame to extract (None = middle frame)
            
        Returns:
            PIL Image
        """
        if frame_index is None:
            frame_index = len(frames) // 2
        
        frame = frames[frame_index]
        return Image.fromarray(frame)
    
    @staticmethod
    def get_video_info(frames: np.ndarray, fps: int = 25) -> dict:
        """
        Get video metadata
        
        Args:
            frames: Video frames array
            fps: Frames per second
            
        Returns:
            Dictionary with video info
        """
        num_frames, height, width, channels = frames.shape
        duration = num_frames / fps
        
        return {
            'num_frames': num_frames,
            'width': width,
            'height': height,
            'channels': channels,
            'fps': fps,
            'duration_seconds': duration,
            'resolution': f"{width}x{height}",
            'aspect_ratio': f"{width//gcd(width, height)}:{height//gcd(width, height)}"
        }


def gcd(a: int, b: int) -> int:
    """Calculate greatest common divisor"""
    while b:
        a, b = b, a % b
    return a
