"""Path management for the application"""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PathManager:
    """Manages application paths and directories"""
    
    def __init__(self):
        # Default paths
        self.app_dir = Path.home() / ".hunyuanvideo"
        self.config_file = self.app_dir / "config.yaml"
        self.cache_dir = Path.home() / ".cache" / "hunyuanvideo"
        
        # Default models path (ComfyUI structure)
        self.default_models_path = self.cache_dir / "models"
        
        # Output directory
        self.default_output_dir = Path.home() / "Videos" / "HunyuanVideo"
        
        # Ensure app directory exists
        self.app_dir.mkdir(parents=True, exist_ok=True)
        
    def get_default_models_path(self) -> Path:
        """Get the default models directory path"""
        return self.default_models_path
    
    def get_output_dir(self) -> Path:
        """Get the output directory path"""
        return self.default_output_dir
    
    def ensure_output_dir(self) -> None:
        """Ensure output directory exists"""
        self.default_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {self.default_output_dir}")
    
    def get_config_path(self) -> Path:
        """Get the configuration file path"""
        return self.config_file
