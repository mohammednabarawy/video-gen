"""Model manager for loading and managing HunyuanVideo models"""

from pathlib import Path
from typing import Optional
import logging
import torch

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages HunyuanVideo model loading and caching"""
    
    def __init__(self, models_base_path: Path):
        """
        Initialize model manager
        
        Args:
            models_base_path: Base path where models are stored (ComfyUI structure)
        """
        self.models_base_path = Path(models_base_path)
        self.device = self._get_device()
        
        # Model components (lazy loaded)
        self.text_encoder = None
        self.diffusion_model = None
        self.vae = None
        self.pipeline = None
        
        logger.info(f"ModelManager initialized with device: {self.device}")
        logger.info(f"Models path: {self.models_base_path}")
    
    def _get_device(self) -> str:
        """Determine the best available device"""
        if torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"GPU detected: {gpu_name} ({vram_gb:.1f} GB VRAM)")
        else:
            device = "cpu"
            logger.warning("No CUDA device found, using CPU (will be slow!)")
        
        return device
    
    def get_vram_gb(self) -> float:
        """Get available VRAM in GB"""
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return 0.0
    
    def should_use_cpu_offload(self) -> bool:
        """Determine if CPU offloading should be used based on VRAM"""
        vram = self.get_vram_gb()
        # Use CPU offload if <24GB VRAM
        return vram > 0 and vram < 24
    
    def get_model_path(self, category: str, filename: str) -> Path:
        """
        Get path to a specific model file
        
        Args:
            category: Model category (text_encoders, diffusion_models, vae)
            filename: Model filename
            
        Returns:
            Full path to model file
        """
        return self.models_base_path / category / filename
    
    def load_pipeline(
        self, 
        model_variant: str = '720p_t2v',
        enable_cpu_offload: Optional[bool] = None,
        enable_vae_tiling: bool = False
    ):
        """
        Load the HunyuanVideo pipeline using diffusers from_pretrained
        
        Note: ComfyUI safetensors files cannot be directly loaded by diffusers
        due to format differences. This method downloads models from Hugging Face.
        
        Args:
            model_variant: Model variant to use ('720p_t2v', '1080p_sr')
            enable_cpu_offload: Whether to use CPU offloading (auto-detect if None)  
            enable_vae_tiling: Whether to enable VAE tiling
            
        Returns:
            Loaded pipeline object or None if failed
        """
        logger.info(f"Loading HunyuanVideo pipeline (variant: {model_variant})...")
        
        try:
            from diffusers import HunyuanVideoPipeline
            
            # Auto-detect CPU offload setting if not specified
            if enable_cpu_offload is None:
                enable_cpu_offload = self.should_use_cpu_offload()
                logger.info(f"Auto-detected CPU offload: {enable_cpu_offload}")
            
            # Use the official HunyuanVideo 1.5 repository
            # This will download all required models (~20GB total)
            repo_id = "tencent/HunyuanVideo-1.5"
            logger.info(f"Loading pipeline from {repo_id}...")
            logger.info("Note: This will download models from Hugging Face (~20GB)")
            logger.info("ComfyUI models cannot be used directly with diffusers due to format differences")
            
            self.pipeline = HunyuanVideoPipeline.from_pretrained(
                repo_id,
                torch_dtype=torch.float16
            )
            
            # Move to device
            if not enable_cpu_offload:
                self.pipeline = self.pipeline.to(self.device)
                logger.info(f"Pipeline loaded to {self.device}")
            else:
                # Enable CPU offloading for lower VRAM usage
                self.pipeline.enable_model_cpu_offload()
                logger.info("CPU offloading enabled")
            
            # Enable VAE tiling if requested (saves VRAM)
            if enable_vae_tiling:
                self.pipeline.vae.enable_tiling()
                logger.info("VAE tiling enabled")
            
            # Enable memory efficient attention if available
            try:
                self.pipeline.enable_xformers_memory_efficient_attention()
                logger.info("Memory efficient attention enabled")
            except Exception:
                logger.warning("xformers not available, using default attention")
            
            logger.info("✓ Pipeline loaded successfully!")
            return self.pipeline
            
        except Exception as e:
            logger.error(f"Error loading pipeline: {e}", exc_info=True)
            return None
    
    def unload_pipeline(self):
        """Unload pipeline to free memory"""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("Pipeline unloaded")
    
    def is_loaded(self) -> bool:
        """Check if pipeline is loaded"""
        return self.pipeline is not None
