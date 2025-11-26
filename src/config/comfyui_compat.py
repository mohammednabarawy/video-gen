"""ComfyUI folder structure compatibility module"""

from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class ComfyUIPathManager:
    """Manages paths compatible with ComfyUI folder structure"""
    
    REQUIRED_SUBDIRS = ['text_encoders', 'diffusion_models', 'vae']
    
    # Common ComfyUI installation paths to check
    COMMON_COMFYUI_PATHS = [
        Path.home() / "ComfyUI" / "models",
        Path("C:/ComfyUI/models"),
        Path("D:/ComfyUI/models"),
        Path("E:/ComfyUI/models"),
        Path("/opt/ComfyUI/models"),
        Path("/usr/local/ComfyUI/models"),
    ]
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize ComfyUI path manager
        
        Args:
            base_path: Base path for models (should point to ComfyUI models directory)
        """
        self.base_path = Path(base_path) if base_path else None
        
    def is_valid_comfyui_structure(self, path: Path) -> bool:
        """
        Check if path has valid ComfyUI models structure
        
        Args:
            path: Path to check
            
        Returns:
            True if path has at least one required subdirectory
        """
        logger.info(f"Validating ComfyUI structure at: {path}")
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return False
        
        # Check for required subdirectories
        found_subdirs = []
        for subdir in self.REQUIRED_SUBDIRS:
            subdir_path = path / subdir
            if subdir_path.exists():
                found_subdirs.append(subdir)
                # Count files in this directory
                file_count = len(list(subdir_path.glob("*.safetensors")))
                logger.info(f"  ✓ Found {subdir}/ with {file_count} .safetensors files")
            else:
                logger.info(f"  ✗ Missing {subdir}/")
        
        has_subdir = len(found_subdirs) > 0
        
        if has_subdir:
            logger.info(f"✓ Valid ComfyUI structure (found {len(found_subdirs)}/{len(self.REQUIRED_SUBDIRS)} subdirs)")
        else:
            logger.warning(f"✗ Invalid ComfyUI structure (no required subdirectories found)")
        
        return has_subdir
    
    def auto_detect_comfyui(self) -> Optional[Path]:
        """
        Attempt to auto-detect ComfyUI installation
        
        Returns:
            Path to ComfyUI models directory if found, None otherwise
        """
        logger.info("Attempting to auto-detect ComfyUI installation...")
        
        for path in self.COMMON_COMFYUI_PATHS:
            if self.is_valid_comfyui_structure(path):
                logger.info(f"ComfyUI installation detected at: {path}")
                return path
        
        logger.info("No ComfyUI installation detected")
        return None
    
    def get_model_path(self, model_type: str, model_name: str) -> Path:
        """
        Get full path for a specific model file
        
        Args:
            model_type: Type of model ('text_encoder', 'diffusion', 'vae')
            model_name: Name of the model file
            
        Returns:
            Full path to the model file
        """
        if not self.base_path:
            raise ValueError("Base path not set. Call set_base_path() first.")
        
        type_map = {
            'text_encoder': 'text_encoders',
            'diffusion': 'diffusion_models',
            'vae': 'vae'
        }
        
        subdir = type_map.get(model_type, model_type)
        return self.base_path / subdir / model_name
    
    def set_base_path(self, path: Path) -> bool:
        """
        Set the base path and validate it
        
        Args:
            path: Path to set as base
            
        Returns:
            True if path is valid, False otherwise
        """
        if self.is_valid_comfyui_structure(path):
            self.base_path = path
            return True
        return False
    
    def get_all_subdirs(self) -> Dict[str, Path]:
        """
        Get all ComfyUI subdirectories
        
        Returns:
            Dictionary mapping subdir names to paths
        """
        if not self.base_path:
            raise ValueError("Base path not set")
        
        return {
            subdir: self.base_path / subdir 
            for subdir in self.REQUIRED_SUBDIRS
        }
    
    def create_structure(self) -> None:
        """Create ComfyUI folder structure if it doesn't exist"""
        if not self.base_path:
            raise ValueError("Base path not set")
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        for subdir in self.REQUIRED_SUBDIRS:
            subdir_path = self.base_path / subdir
            subdir_path.mkdir(exist_ok=True)
            logger.info(f"Created directory: {subdir_path}")
