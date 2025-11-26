"""Alternative model manager using ComfyUI backend to load models"""

from pathlib import Path
from typing import Optional
import logging
import sys

logger = logging.getLogger(__name__)


class ComfyUIModelManager:
    """Manages HunyuanVideo model loading using ComfyUI backend"""
    
    def __init__(self, comfyui_path: Path, models_base_path: Path):
        """
        Initialize model manager with ComfyUI backend
        
        Args:
            comfyui_path: Path to ComfyUI installation
            models_base_path: Base path where models are stored
        """
        self.comfyui_path = Path(comfyui_path)
        self.models_base_path = Path(models_base_path)
        
        # Add ComfyUI to Python path
        if str(self.comfyui_path) not in sys.path:
            sys.path.insert(0, str(self.comfyui_path))
        
        # Import ComfyUI modules
        try:
            import folder_paths
            import nodes
            self.folder_paths = folder_paths
            self.nodes = nodes
            
            # Set model paths
            folder_paths.set_output_directory(str(self.models_base_path.parent / "output"))
            folder_paths.add_model_folder_path("diffusion_models", str(self.models_base_path / "diffusion_models"))
            folder_paths.add_model_folder_path("vae", str(self.models_base_path / "vae"))
            folder_paths.add_model_folder_path("text_encoders", str(self.models_base_path / "text_encoders"))
            
            logger.info("ComfyUI backend initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ComfyUI backend: {e}")
            raise
        
        self.model = None
        self.vae = None
        self.clip = None
    
    def load_models(self):
        """Load HunyuanVideo models using ComfyUI loaders"""
        logger.info("Loading models using ComfyUI backend...")
        
        try:
            # Load UNET (Transformer)
            unet_loader = self.nodes.UNETLoader()
            self.model = unet_loader.load_unet("hunyuanvideo1.5_720p_t2v_fp16.safetensors")[0]
            logger.info("✓ Loaded Transformer model")
            
            # Load VAE
            vae_loader = self.nodes.VAELoader()
            self.vae = vae_loader.load_vae("hunyuanvideo15_vae_fp16.safetensors")[0]
            logger.info("✓ Loaded VAE model")
            
            # Load CLIP (Text Encoders)
            clip_loader = self.nodes.DualCLIPLoader()
            self.clip = clip_loader.load_clip(
                "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "byt5_small_glyphxl_fp16.safetensors",
                "hunyuan_video_15"
            )[0]
            logger.info("✓ Loaded text encoders")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}", exc_info=True)
            return False
    
    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1280,
        height: int = 720,
        num_frames: int = 125,
        steps: int = 50,
        cfg: float = 7.0,
        seed: Optional[int] = None
    ):
        """
        Generate video using ComfyUI nodes
        
        Args:
            prompt: Text prompt
            negative_prompt: Negative prompt
            width: Video width
            height: Video height
            num_frames: Number of frames
            steps: Inference steps
            cfg: CFG scale
            seed: Random seed
            
        Returns:
            Generated latent or None if failed
        """
        if not all([self.model, self.vae, self.clip]):
            logger.error("Models not loaded. Call load_models() first.")
            return None
        
        try:
            import random
            if seed is None:
                seed = random.randint(0, 2**32 - 1)
            
            # Encode prompt
            clip_text_encode = self.nodes.CLIPTextEncode()
            positive_cond = clip_text_encode.encode(self.clip, prompt)[0]
            negative_cond = clip_text_encode.encode(self.clip, negative_prompt)[0]
            
            # Create empty latent
            empty_latent = self.nodes.EmptyLatentVideo()
            latent = empty_latent.generate(width, height, num_frames, 1)[0]
            
            # Sample
            ksampler = self.nodes.KSampler()
            sampled_latent = ksampler.sample(
                self.model,
                seed,
                steps,
                cfg,
                "euler",  # sampler_name
                "normal",  # scheduler
                positive_cond,
                negative_cond,
                latent,
                1.0  # denoise
            )[0]
            
            # Decode
            vae_decode = self.nodes.VAEDecode()
            frames = vae_decode.decode(sampled_latent, self.vae)[0]
            
            return frames
            
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            return None
