"""
Application Settings

Comprehensive settings system for HunyuanVideo Generator.
Inspired by Krita AI Diffusion's settings architecture.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ServerMode(Enum):
    """Server connection mode"""
    UNDEFINED = "undefined"
    MANAGED = "managed"  # App manages ComfyUI server
    EXTERNAL = "external"  # Connect to existing server
    

class ServerBackend(Enum):
    """ComfyUI server backend"""
    CUDA = ("CUDA (NVIDIA GPU)", True)
    CPU = ("CPU", True)
    DIRECTML = ("DirectML (GPU)", True)
    
    @staticmethod
    def supported():
        return [b for b in ServerBackend if b.value[1]]
    
    @staticmethod
    def default():
        return ServerBackend.CUDA


class PerformancePreset(Enum):
    """Performance presets"""
    AUTO = "auto"
    LOW = "low"  # Up to 8GB VRAM
    MEDIUM = "medium"  # 8-16GB VRAM
    HIGH = "high"  # 16GB+ VRAM
    CUSTOM = "custom"


class VideoFormat(Enum):
    """Output video format"""
    MP4_H264 = "MP4 (H.264)"
    MP4_H265 = "MP4 (H.265/HEVC)"
    WEBM_VP9 = "WebM (VP9)"
    GIF = "GIF"


@dataclass
class PerformancePresetSettings:
    """Settings for a performance preset"""
    enable_cpu_offload: bool = False
    enable_vae_tiling: bool = False
    max_resolution: str = "720p"
    max_frames: int = 125


class AppSettings:
    """Main application settings"""
    
    # Performance presets configuration
    _performance_presets = {
        PerformancePreset.LOW: PerformancePresetSettings(
            enable_cpu_offload=True,
            enable_vae_tiling=True,
            max_resolution="480p",
            max_frames=49  # ~2 seconds at 24fps for 12GB VRAM
        ),
        PerformancePreset.MEDIUM: PerformancePresetSettings(
            enable_cpu_offload=False,
            enable_vae_tiling=True,
            max_resolution="720p",
            max_frames=73  # ~3 seconds at 24fps for 16GB+ VRAM
        ),
        PerformancePreset.HIGH: PerformancePresetSettings(
            enable_cpu_offload=False,
            enable_vae_tiling=False,
            max_resolution="1080p",
            max_frames=125  # ~5 seconds at 24fps for 24GB+ VRAM
        ),
    }
    
    def __init__(self, settings_path: Optional[Path] = None):
        """
        Initialize settings
        
        Args:
            settings_path: Path to settings file (default: user data dir)
        """
        if settings_path is None:
            from pathlib import Path
            import os
            if os.name == 'nt':  # Windows
                app_data = Path(os.environ.get('APPDATA', Path.home()))
                settings_path = app_data / "HunyuanVideoGenerator" / "settings.json"
            else:
                settings_path = Path.home() / ".config" / "HunyuanVideoGenerator" / "settings.json"
        
        self.settings_path = Path(settings_path)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize default settings
        self._init_defaults()
        
        # Load from file if exists
        self.load()
    
    def _init_defaults(self):
        """Initialize default settings"""
        # Connection settings
        self.server_mode = ServerMode.MANAGED
        self.comfyui_path = ""
        self.server_url = "127.0.0.1:8188"
        self.server_backend = ServerBackend.CUDA
        self.server_arguments = ""
        self.auto_start_server = True
        
        # Model settings
        self.models_path = ""
        self.use_comfyui_models = True
        self.auto_download_models = True
        self.check_models_on_startup = True
        
        # Generation settings
        self.default_resolution = "720p"
        self.default_aspect_ratio = "16:9"
        self.default_duration = 5
        self.default_fps = 25
        self.default_style = "Cinematic"
        self.default_cfg_scale = 7.0
        self.default_inference_steps = 20  # Reduced for Low VRAM compatibility
        
        # Performance settings
        self.performance_preset = PerformancePreset.AUTO
        self.enable_cpu_offload = False
        self.enable_vae_tiling = False
        self.enable_xformers = True
        
        # Output settings
        self.default_output_format = VideoFormat.MP4_H264
        self.output_quality = 23  # CRF value (lower = better quality)
        self.save_metadata = True
        
        # UI settings
        self.show_advanced_options = False
        self.confirm_before_generation = False
        self.auto_open_output = True
        
        # Advanced settings
        self.enable_prompt_rewriting = True
        self.enable_super_resolution = False
        self.debug_mode = False
        self.log_level = "INFO"
    
    def load(self) -> bool:
        """
        Load settings from file
        
        Returns:
            True if loaded successfully
        """
        if not self.settings_path.exists():
            logger.info("Settings file not found, using defaults")
            return False
        
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load each setting
            for key, value in data.items():
                if hasattr(self, key):
                    # Handle enums
                    attr_type = type(getattr(self, key))
                    if isinstance(getattr(self, key), Enum):
                        try:
                            setattr(self, key, attr_type(value))
                        except (ValueError, KeyError):
                            logger.warning(f"Invalid enum value for {key}: {value}")
                    else:
                        setattr(self, key, value)
            
            logger.info(f"Settings loaded from {self.settings_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return False
    
    def save(self) -> bool:
        """
        Save settings to file
        
        Returns:
            True if saved successfully
        """
        try:
            # Convert settings to dict
            data = {}
            for key in dir(self):
                if key.startswith('_') or key in ['settings_path', 'load', 'save', 'get', 'set', 'apply_performance_preset']:
                    continue
                
                value = getattr(self, key)
                if callable(value):
                    continue
                
                # Handle enums
                if isinstance(value, Enum):
                    data[key] = value.value
                else:
                    data[key] = value
            
            # Save to file
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Settings saved to {self.settings_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value"""
        setattr(self, key, value)
    
    def apply_performance_preset(self, preset: PerformancePreset):
        """
        Apply a performance preset
        
        Args:
            preset: Performance preset to apply
        """
        if preset == PerformancePreset.AUTO:
            # Auto-detect based on VRAM
            import torch
            if torch.cuda.is_available():
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                if vram_gb < 8:
                    preset = PerformancePreset.LOW
                elif vram_gb < 16:
                    preset = PerformancePreset.MEDIUM
                else:
                    preset = PerformancePreset.HIGH
            else:
                preset = PerformancePreset.LOW
        
        if preset == PerformancePreset.CUSTOM:
            return  # Don't override custom settings
        
        if preset in self._performance_presets:
            preset_settings = self._performance_presets[preset]
            self.enable_cpu_offload = preset_settings.enable_cpu_offload
            self.enable_vae_tiling = preset_settings.enable_vae_tiling
            self.default_resolution = preset_settings.max_resolution
            
            logger.info(f"Applied performance preset: {preset.value}")
