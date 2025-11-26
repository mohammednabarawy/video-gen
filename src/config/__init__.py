"""Configuration module for the video generator"""

from .settings import Settings
from .paths import PathManager
from .comfyui_compat import ComfyUIPathManager

__all__ = ['Settings', 'PathManager', 'ComfyUIPathManager']
