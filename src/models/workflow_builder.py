"""
ComfyUI Workflow Builder for HunyuanVideo

Programmatically constructs ComfyUI workflows in API format.
Based on official HunyuanVideo 1.5 workflows from Comfy-Org.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class HunyuanVideoWorkflowBuilder:
    """Builds ComfyUI workflows programmatically for HunyuanVideo"""
    
    def __init__(self):
        self.node_id_counter = 1
        self.workflow = {}
        
    def _next_id(self) -> str:
        """Generate next node ID"""
        node_id = str(self.node_id_counter)
        self.node_id_counter += 1
        return node_id
        
    def build_t2v_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1280,
        height: int = 720,
        num_frames: int = 129,
        steps: int = 50,
        cfg: float = 7.0,
        seed: Optional[int] = None,
        fps: int = 24,
        enable_vae_tiling: bool = False,
        low_vram: bool = False
    ) -> Dict[str, Any]:
        """
        Build a Text-to-Video workflow for HunyuanVideo
        
        Based on official video_hunyuan_video_1.5_720p_t2v.json workflow.
        
        Args:
            prompt: Text prompt
            negative_prompt: Negative prompt
            width: Video width
            height: Video height
            num_frames: Number of frames
            steps: Inference steps
            cfg: CFG scale
            seed: Random seed (None for random)
            fps: Frames per second
            enable_vae_tiling: Enable VAE tiling for lower VRAM
            low_vram: Enable Low VRAM mode (FP8 weights)
            
        Returns:
            Workflow dictionary in ComfyUI API format
        """
        self.workflow = {}
        self.node_id_counter = 1
        
        # Node 1: DualCLIPLoader (text encoders)
        clip_loader_id = self._next_id()
        self.workflow[clip_loader_id] = {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "clip_name2": "byt5_small_glyphxl_fp16.safetensors",
                "type": "hunyuan_video_15",
                "device_mode": "default"
            }
        }
        
        # Node 2: UNETLoader (model)
        unet_loader_id = self._next_id()
        weight_dtype = "fp8_e4m3fn" if low_vram else "default"
        
        self.workflow[unet_loader_id] = {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "hunyuanvideo1.5_720p_t2v_fp16.safetensors",
                "weight_dtype": weight_dtype
            }
        }
        
        # Node 3: VAELoader
        vae_loader_id = self._next_id()
        self.workflow[vae_loader_id] = {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "hunyuanvideo15_vae_fp16.safetensors"
            }
        }
        
        # Node 4: CLIPTextEncode (positive)
        text_encode_pos_id = self._next_id()
        self.workflow[text_encode_pos_id] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": [clip_loader_id, 0]
            }
        }
        
        # Node 5: CLIPTextEncode (negative)
        text_encode_neg_id = self._next_id()
        self.workflow[text_encode_neg_id] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": [clip_loader_id, 0]
            }
        }
        
        # Node 6: EmptyLatentImage (create empty latent)
        # Note: HunyuanVideo uses standard EmptyLatentImage with length parameter
        empty_latent_id = self._next_id()
        self.workflow[empty_latent_id] = {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": num_frames  # For video, batch_size = number of frames
            }
        }
        
        # Node 7: ModelSamplingSD3 (shift configuration)
        model_sampling_id = self._next_id()
        self.workflow[model_sampling_id] = {
            "class_type": "ModelSamplingSD3",
            "inputs": {
                "model": [unet_loader_id, 0],
                "shift": 9  # 9 for 720p T2V according to official settings
            }
        }
        
        # Node 8: CFGGuider
        cfg_guider_id = self._next_id()
        self.workflow[cfg_guider_id] = {
            "class_type": "CFGGuider",
            "inputs": {
                "model": [model_sampling_id, 0],
                "positive": [text_encode_pos_id, 0],
                "negative": [text_encode_neg_id, 0],
                "cfg": cfg
            }
        }
        
        # Node 9: BasicScheduler
        scheduler_id = self._next_id()
        self.workflow[scheduler_id] = {
            "class_type": "BasicScheduler",
            "inputs": {
                "model": [model_sampling_id, 0],
                "scheduler": "simple",
                "steps": steps,
                "denoise": 1.0
            }
        }
        
        # Node 10: KSamplerSelect
        sampler_select_id = self._next_id()
        self.workflow[sampler_select_id] = {
            "class_type": "KSamplerSelect",
            "inputs": {
                "sampler_name": "euler"
            }
        }
        
        # Node 11: RandomNoise
        noise_id = self._next_id()
        # Use random seed generation - 0 means random in ComfyUI
        import random
        actual_seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        self.workflow[noise_id] = {
            "class_type": "RandomNoise",
            "inputs": {
                "noise_seed": actual_seed
            }
        }
        
        # Node 12: SamplerCustomAdvanced
        sampler_id = self._next_id()
        self.workflow[sampler_id] = {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": [noise_id, 0],
                "guider": [cfg_guider_id, 0],
                "sampler": [sampler_select_id, 0],
                "sigmas": [scheduler_id, 0],
                "latent_image": [empty_latent_id, 0]
            }
        }
        
        # Node 13: VAEDecode
        vae_decode_id = self._next_id()
        if enable_vae_tiling:
            self.workflow[vae_decode_id] = {
                "class_type": "VAEDecodeTiled",
                "inputs": {
                    "samples": [sampler_id, 0],
                    "vae": [vae_loader_id, 0],
                    "tile_size": 512,
                    "overlap": 64,  # Spatial overlap for tiling
                    "temporal_size": 16,  # Number of frames processed per batch
                    "temporal_overlap": 4  # Temporal overlap between batches
                }
            }
        else:
            self.workflow[vae_decode_id] = {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": [sampler_id, 0],
                    "vae": [vae_loader_id, 0]
                }
            }
        
        # Node 14: CreateVideo
        create_video_id = self._next_id()
        self.workflow[create_video_id] = {
            "class_type": "CreateVideo",
            "inputs": {
                "images": [vae_decode_id, 0],
                "fps": fps
            }
        }
        
        # Node 15: SaveVideo
        save_video_id = self._next_id()
        self.workflow[save_video_id] = {
            "class_type": "SaveVideo",
            "inputs": {
                "video": [create_video_id, 0],
                "filename_prefix": "video/hunyuan_video_1.5",
                "format": "video/h264-mp4",
                "codec": "h264",  # Required codec parameter
                "pingpong": False,
                "save_output": True
            }
        }
        
        return self.workflow
    
    def build_i2v_workflow(
        self,
        prompt: str,
        image_path: str,
        negative_prompt: str = "",
        width: int = 1280,
        height: int = 720,
        num_frames: int = 129,
        steps: int = 50,
        cfg: float = 7.0,
        seed: Optional[int] = None,
        fps: int = 24,
        enable_vae_tiling: bool = False,
        low_vram: bool = False
    ) -> Dict[str, Any]:
        """
        Build an Image-to-Video workflow for HunyuanVideo
        
        Args:
            prompt: Text prompt
            image_path: Path to input image
            negative_prompt: Negative prompt
            width: Video width
            height: Video height
            num_frames: Number of frames
            steps: Inference steps
            cfg: CFG scale
            seed: Random seed
            fps: Frames per second
            enable_vae_tiling: Enable VAE tiling
            low_vram: Enable Low VRAM mode
            
        Returns:
            Workflow dictionary in ComfyUI API format
        """
        # For I2V, use T2V workflow with different model and add image conditioning
        # This is a simplified version - full I2V requires additional nodes
        self.workflow = self.build_t2v_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            steps=steps,
            cfg=cfg,
            seed=seed,
            fps=fps,
            enable_vae_tiling=enable_vae_tiling,
            low_vram=low_vram
        )
        
        # Update model to I2V version
        for node_id, node in self.workflow.items():
            if node.get("class_type") == "UNETLoader":
                node["inputs"]["unet_name"] = "hunyuanvideo1.5_720p_i2v_fp16.safetensors"
            # Adjust shift for I2V
            elif node.get("class_type") == "ModelSamplingSD3":
                node["inputs"]["shift"] = 7  # 7 for 720p I2V
        
        logger.warning("I2V workflow needs image conditioning nodes - using simplified T2V for now")
        
        return self.workflow
