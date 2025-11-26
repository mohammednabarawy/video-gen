"""
ComfyUI Integration Module

This module provides integration with an existing ComfyUI installation,
allowing the app to use ComfyUI's model loading and inference capabilities.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import logging
import sys
import json

logger = logging.getLogger(__name__)


class ComfyUIIntegration:
    """Manages integration with ComfyUI installation"""
    
    def __init__(self, comfyui_path: str):
        """
        Initialize ComfyUI integration
        
        Args:
            comfyui_path: Path to ComfyUI installation (e.g., D:\\ComfyUI_windows_portable\\ComfyUI)
        """
        self.comfyui_path = Path(comfyui_path)
        self.initialized = False
        
        if not self.comfyui_path.exists():
            raise ValueError(f"ComfyUI path does not exist: {self.comfyui_path}")
        
        logger.info(f"ComfyUI integration initialized with path: {self.comfyui_path}")
    
    def initialize(self) -> bool:
        """
        Initialize ComfyUI modules
        
        Returns:
            True if successful, False otherwise
        """
        if self.initialized:
            return True
        
        try:
            # Add ComfyUI to Python path
            comfyui_str = str(self.comfyui_path)
            if comfyui_str not in sys.path:
                sys.path.insert(0, comfyui_str)
                logger.info(f"Added {comfyui_str} to Python path")
            
            # Import ComfyUI modules
            import folder_paths
            import nodes
            
            # Store references
            self.folder_paths = folder_paths
            self.nodes = nodes
            
            logger.info("✓ ComfyUI modules imported successfully")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ComfyUI: {e}", exc_info=True)
            return False
    
    def load_workflow(self, workflow_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a ComfyUI workflow JSON file
        
        Args:
            workflow_path: Path to workflow JSON file
            
        Returns:
            Workflow data or None if failed
        """
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            logger.info(f"Loaded workflow from {workflow_path}")
            return workflow
        except Exception as e:
            logger.error(f"Failed to load workflow: {e}")
            return None
    
    def get_model_paths(self) -> Dict[str, Path]:
        """
        Get paths to model directories
        
        Returns:
            Dictionary mapping model types to their paths
        """
        if not self.initialized:
            if not self.initialize():
                return {}
        
        models_path = self.comfyui_path / "models"
        
        return {
            "diffusion_models": models_path / "diffusion_models",
            "vae": models_path / "vae",
            "text_encoders": models_path / "text_encoders",
            "clip": models_path / "clip",
            "clip_vision": models_path / "clip_vision",
            "checkpoints": models_path / "checkpoints",
            "loras": models_path / "loras",
            "controlnet": models_path / "controlnet",
            "upscale_models": models_path / "upscale_models",
        }
    
    def list_available_models(self, model_type: str) -> list:
        """
        List available models of a specific type
        
        Args:
            model_type: Type of model (e.g., 'diffusion_models', 'vae')
            
        Returns:
            List of model filenames
        """
        model_paths = self.get_model_paths()
        if model_type not in model_paths:
            logger.warning(f"Unknown model type: {model_type}")
            return []
        
        model_dir = model_paths[model_type]
        if not model_dir.exists():
            logger.warning(f"Model directory does not exist: {model_dir}")
            return []
        
        # List all .safetensors and .pt files
        models = []
        for ext in ['.safetensors', '.pt', '.ckpt', '.pth']:
            models.extend([f.name for f in model_dir.rglob(f'*{ext}')])
        
        return sorted(models)
