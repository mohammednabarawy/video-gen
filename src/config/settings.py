"""Application settings and configuration management"""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import logging

logger = logging.getLogger(__name__)


class Settings:
    """Manages application settings with persistence"""
    
    # Default settings
    DEFAULTS = {
        # Model paths
        'use_comfyui_models': False,
        'comfyui_models_path': None,
        'custom_models_path': None,
        'auto_detect_comfyui': True,
        
        # Output settings
        'default_output_dir': None,
        
        # Generation defaults
        'default_resolution': '720p',
        'default_duration': 5,  # seconds
        'default_aspect_ratio': '16:9',
        'default_fps': 25,
        'default_cfg_scale': 7.0,
        'default_inference_steps': 50,
        'default_style': 'Cinematic',
        
        # Advanced settings
        'enable_prompt_rewriting': False,
        'enable_super_resolution': False,
        'enable_cpu_offload': False,  # Auto-detect based on VRAM
        'enable_vae_tiling': False,
        
        # GUI preferences
        'window_width': 900,
        'window_height': 800,
        'theme': 'system',
        'language': 'en',
        
        # History
        'recent_prompts': [],
        'max_recent_prompts': 10,
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize settings
        
        Args:
            config_path: Path to configuration file
        """
        from .paths import PathManager
        
        self.path_manager = PathManager()
        self.config_path = config_path or self.path_manager.get_config_path()
        self.settings: Dict[str, Any] = self.DEFAULTS.copy()
        
        # Load existing settings
        self.load()
    
    def load(self) -> None:
        """Load settings from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_settings = yaml.safe_load(f) or {}
                    self.settings.update(loaded_settings)
                logger.info(f"Settings loaded from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
        else:
            logger.info("No existing settings file found, using defaults")
    
    def save(self) -> None:
        """Save settings to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False)
            logger.info(f"Settings saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self.settings[key] = value
    
    def get_models_path(self) -> Optional[Path]:
        """Get the configured models path"""
        if self.get('use_comfyui_models') and self.get('comfyui_models_path'):
            return Path(self.get('comfyui_models_path'))
        elif self.get('custom_models_path'):
            return Path(self.get('custom_models_path'))
        else:
            return self.path_manager.get_default_models_path()
    
    def set_models_path(self, path: Path, use_comfyui: bool = False) -> None:
        """Set the models path"""
        if use_comfyui:
            self.set('use_comfyui_models', True)
            self.set('comfyui_models_path', str(path))
        else:
            self.set('use_comfyui_models', False)
            self.set('custom_models_path', str(path))
        self.save()
    
    def add_recent_prompt(self, prompt: str) -> None:
        """Add a prompt to recent history"""
        recent = self.get('recent_prompts', [])
        
        # Remove duplicate if exists
        if prompt in recent:
            recent.remove(prompt)
        
        # Add to front
        recent.insert(0, prompt)
        
        # Limit to max
        max_prompts = self.get('max_recent_prompts', 10)
        recent = recent[:max_prompts]
        
        self.set('recent_prompts', recent)
        self.save()
    
    def get_recent_prompts(self) -> list:
        """Get list of recent prompts"""
        return self.get('recent_prompts', [])
