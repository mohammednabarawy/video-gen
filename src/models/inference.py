"""HunyuanVideo inference wrapper"""

from pathlib import Path
from typing import Optional, Callable, Dict, Any
from PIL import Image
import torch
import logging
import numpy as np
import json
import random

from config.app_settings import AppSettings, ServerMode
from .comfyui_client import ComfyUIClient

logger = logging.getLogger(__name__)


class HunyuanVideoInference:
    """High-level API for HunyuanVideo generation"""
    
    # Preset resolutions (width x height)
    RESOLUTIONS = {
        '480p': (854, 480),
        '720p': (1280, 720),
        '1080p': (1920, 1080)
    }
    
    # Aspect ratios
    ASPECT_RATIOS = {
        '16:9': (16, 9),
        '9:16': (9, 16),
        '1:1': (1, 1),
        '4:3': (4, 3),
        '21:9': (21, 9)
    }
    
    # Camera motion presets
    CAMERA_MOTIONS = [
        'static', 'zoom_in', 'zoom_out', 'pan_left', 'pan_right',
        'tilt_up', 'tilt_down', 'orbit', 'dynamic'
    ]
    
    # Style presets
    STYLE_PRESETS = {
        'Cinematic': 'cinematic, film grain, professional lighting, dramatic',
        'Realistic': 'photorealistic, high quality, detailed',
        'Anime': 'anime style, vibrant colors, detailed animation',
        '3D': '3d render, octane render, high quality',
        'Artistic': 'artistic, stylized, creative'
    }
    
    def __init__(self, model_manager, app_settings: Optional[AppSettings] = None, comfyui_client: Optional[ComfyUIClient] = None):
        """
        Initialize inference wrapper
        
        Args:
            model_manager: ModelManager instance
            app_settings: AppSettings instance
            comfyui_client: ComfyUIClient instance
        """
        self.model_manager = model_manager
        self.app_settings = app_settings
        self.comfyui_client = comfyui_client
        self.pipeline = None
    
    def _ensure_pipeline_loaded(self, **kwargs):
        """Ensure pipeline is loaded"""
        if not self.model_manager.is_loaded():
            logger.info("Pipeline not loaded, loading now...")
            self.pipeline = self.model_manager.load_pipeline(**kwargs)
        else:
            self.pipeline = self.model_manager.pipeline
        
        return self.pipeline is not None
    
    def _calculate_dimensions(
        self, 
        resolution: str = '720p',
        aspect_ratio: str = '16:9'
    ) -> tuple:
        """
        Calculate width and height based on resolution and aspect ratio
        
        Args:
            resolution: Resolution preset
            aspect_ratio: Aspect ratio preset
            
        Returns:
            (width, height) tuple
        """
        if resolution in self.RESOLUTIONS:
            return self.RESOLUTIONS[resolution]
        
        # Custom calculation based on aspect ratio
        base_width, base_height = self.RESOLUTIONS.get('720p', (1280, 720))
        ar_w, ar_h = self.ASPECT_RATIOS.get(aspect_ratio, (16, 9))
        
        # Maintain area, adjust for aspect ratio
        area = base_width * base_height
        height = int((area * ar_h / ar_w) ** 0.5)
        width = int(height * ar_w / ar_h)
        
        # Round to nearest multiple of 8 (required by model)
        width = (width // 8) * 8
        height = (height // 8) * 8
        
        return width, height
    
    def _enhance_prompt(
        self, 
        prompt: str,
        style: Optional[str] = None,
        camera_motion: Optional[str] = None
    ) -> str:
        """
        Enhance prompt with style and camera motion
        
        Args:
            prompt: Base prompt
            style: Style preset name
            camera_motion: Camera motion type
            
        Returns:
            Enhanced prompt
        """
        enhanced = prompt
        
        # Add style
        if style and style in self.STYLE_PRESETS:
            style_desc = self.STYLE_PRESETS[style]
            enhanced = f"{enhanced}, {style_desc}"
        
        # Add camera motion
        if camera_motion and camera_motion in self.CAMERA_MOTIONS:
            motion_desc = camera_motion.replace('_', ' ')
            enhanced = f"{enhanced}, camera {motion_desc}"
        
        return enhanced
    
    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        image: Optional[Image.Image] = None,
        num_frames: int = 129,  # ~5 seconds at 25 FPS
        resolution: str = '720p',
        aspect_ratio: str = '16:9',
        fps: int = 25,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.0,
        seed: Optional[int] = None,
        style: Optional[str] = None,
        camera_motion: Optional[str] = None,
        enable_prompt_rewriting: bool = False,
        enable_cpu_offload: Optional[bool] = None,
        enable_vae_tiling: bool = False,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        preview_callback: Optional[Callable[[bytes, str], None]] = None,
        **kwargs
    ) -> Optional[np.ndarray]:
        """
        Generate video from text or image
        
        Args:
            prompt: Text description of the video
            negative_prompt: What to avoid in the video
            image: Input image for I2V (None for T2V)
            num_frames: Number of frames to generate
            resolution: Resolution preset ('480p', '720p', '1080p')
            aspect_ratio: Aspect ratio ('16:9', '9:16', etc.)
            fps: Frames per second
            num_inference_steps: Number of denoising steps
            guidance_scale: CFG scale (higher = more prompt adherence)
            seed: Random seed for reproducibility
            style: Style preset name
            camera_motion: Camera motion type
            enable_prompt_rewriting: Use AI to enhance prompt
            enable_cpu_offload: Enable CPU offloading for lower VRAM
            enable_vae_tiling: Enable VAE tiling for lower VRAM
            progress_callback: Function(step, total_steps, latency) for progress
            **kwargs: Additional arguments
            
        Returns:
            Generated video as numpy array (frames, height, width, channels)
            or None if generation failed
        """
        logger.info("Starting video generation...")
        logger.info(f"Prompt: {prompt}")
        
        # Check if we should use ComfyUI
        if self.app_settings and self.app_settings.server_mode != ServerMode.UNDEFINED and self.comfyui_client:
            return self._generate_with_comfyui(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=image,
                num_frames=num_frames,
                resolution=resolution,
                fps=fps,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=seed,
                style=style,
                camera_motion=camera_motion,
                progress_callback=progress_callback,
                preview_callback=preview_callback,
                **kwargs
            )

        # Ensure pipeline is loaded (Local Diffusers Fallback)
        if not self._ensure_pipeline_loaded(
            enable_cpu_offload=enable_cpu_offload,
            enable_vae_tiling=enable_vae_tiling
        ):
            logger.error("Failed to load pipeline")
            return None
        
        try:
            # Calculate dimensions
            width, height = self._calculate_dimensions(resolution, aspect_ratio)
            logger.info(f"Resolution: {width}x{height}, Frames: {num_frames}, FPS: {fps}")
            
            # Enhance prompt if requested
            if style or camera_motion:
                enhanced_prompt = self._enhance_prompt(prompt, style, camera_motion)
                logger.info(f"Enhanced prompt: {enhanced_prompt}")
            else:
                enhanced_prompt = prompt
            
            # Set random seed if provided
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.model_manager.device)
                generator.manual_seed(seed)
                logger.info(f"Using seed: {seed}")
            
            # Prepare generation arguments
            gen_args = {
                'prompt': enhanced_prompt,
                'negative_prompt': negative_prompt,
                'num_frames': num_frames,
                'height': height,
                'width': width,
                'num_inference_steps': num_inference_steps,
                'guidance_scale': guidance_scale,
                'generator': generator,
            }
            
            # Add image for I2V if provided
            if image is not None:
                gen_args['image'] = image
                logger.info("Image-to-Video mode")
            else:
                logger.info("Text-to-Video mode")
            
            # Progress callback wrapper
            if progress_callback:
                def callback_fn(pipe, step, timestep, callback_kwargs):
                    progress_callback(step, num_inference_steps, 0.0)
                    return callback_kwargs
                
                gen_args['callback_on_step_end'] = callback_fn
            
            # Generate video
            logger.info("Running inference...")
            output = self.pipeline(**gen_args)
            
            # Extract video frames
            video_frames = output.frames[0]  # Shape: (num_frames, height, width, 3)
            
            logger.info(f"✓ Video generated! Shape: {video_frames.shape}")
            return video_frames
            
        except Exception as e:
            logger.error(f"Error during video generation: {e}", exc_info=True)
            return None
    
    def _generate_with_comfyui(self, **kwargs) -> Optional[np.ndarray]:
        """Generate video using ComfyUI backend"""
        logger.info("Generating with ComfyUI...")
        
        if not self.comfyui_client.is_server_running():
            logger.error("ComfyUI server is not running")
            return None
            
        # Connect to WebSocket for real-time updates
        try:
            self.comfyui_client.connect()
            
            # Register callbacks
            progress_callback = kwargs.get('progress_callback')
            preview_callback = kwargs.get('preview_callback')
            
            if progress_callback:
                def on_progress(data):
                    # data = {'value': 1, 'max': 20}
                    value = data.get('value', 0)
                    max_val = data.get('max', 1)
                    progress_callback(value, max_val, 0.0)
                self.comfyui_client.register_callback('progress', on_progress)
                
            if preview_callback:
                self.comfyui_client.register_callback('preview', preview_callback)
                
        except Exception as e:
            logger.warning(f"Failed to connect to WebSocket: {e}")

        try:
            from .workflow_builder import HunyuanVideoWorkflowBuilder
            
            # Extract parameters
            prompt = kwargs.get('prompt', '')
            negative_prompt = kwargs.get('negative_prompt', '')
            image = kwargs.get('image')
            resolution = kwargs.get('resolution', '720p')
            num_frames = kwargs.get('num_frames', 129)
            num_inference_steps = kwargs.get('num_inference_steps', 50)
            guidance_scale = kwargs.get('guidance_scale', 7.0)
            seed = kwargs.get('seed')
            
            # Calculate dimensions
            width, height = self._calculate_dimensions(
                resolution=resolution,
                aspect_ratio=kwargs.get('aspect_ratio', '16:9')
            )
            
            logger.info(f"Building workflow for {width}x{height}, {num_frames} frames")
            
            # Build workflow
            builder = HunyuanVideoWorkflowBuilder()
            
            if image is not None:
                # Image-to-Video
                logger.info("Building I2V workflow")
                # For now, we'll use T2V as I2V requires uploading the image first
                logger.warning("I2V not fully implemented in ComfyUI backend yet, using T2V")
                workflow = builder.build_t2v_workflow(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_frames=num_frames,
                    steps=num_inference_steps,
                    cfg=guidance_scale,
                    seed=seed
                )
            else:
                # Text-to-Video
                logger.info("Building T2V workflow")
                workflow = builder.build_t2v_workflow(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_frames=num_frames,
                    steps=num_inference_steps,
                    cfg=guidance_scale,
                    seed=seed
                )
            
            logger.info(f"Workflow constructed with {len(workflow)} nodes")
            
            # Queue prompt
            prompt_id = self.comfyui_client.queue_prompt(workflow)
            if not prompt_id:
                logger.error("Failed to queue workflow")
                return None
            
            logger.info(f"Workflow queued: {prompt_id}")
                
            # Wait for completion
            logger.info("Waiting for generation to complete...")
            if self.comfyui_client.wait_for_completion(prompt_id, timeout=600):
                # Get output
                outputs = self.comfyui_client.get_output_images(prompt_id)
                if outputs:
                    logger.info(f"Generation complete! Found {len(outputs)} output(s)")
                    # Download first output
                    out_file = outputs[0]
                    video_data = self.comfyui_client.download_output(
                        out_file['filename'], 
                        out_file['subfolder'], 
                        out_file['type']
                    )
                    
                    if video_data:
                        # Convert bytes to numpy array (this is complex for video)
                        # For now, save to temp file and load
                        import tempfile
                        import imageio
                        
                        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                            tmp.write(video_data)
                            tmp_path = tmp.name
                            
                        logger.info(f"Video saved to temp file: {tmp_path}")
                        
                        # Read video
                        reader = imageio.get_reader(tmp_path)
                        frames = []
                        for frame in reader:
                            frames.append(frame)
                        
                        logger.info(f"Loaded {len(frames)} frames")
                        return np.array(frames)
                else:
                    logger.error("No outputs found")
            else:
                logger.error("Generation timed out or failed")
                        
            return None
            
        except Exception as e:
            logger.error(f"Error in ComfyUI generation: {e}", exc_info=True)
            return None
            
        finally:
            # Always disconnect WebSocket
            if self.comfyui_client:
                self.comfyui_client.disconnect()

    def save_video(
        self,
        video_frames: np.ndarray,
        output_path: Path,
        fps: int = 25
    ) -> bool:
        """
        Save video frames to file
        
        Args:
            video_frames: Video as numpy array
            output_path: Output file path
            fps: Frames per second
            
        Returns:
            True if successful
        """
        try:
            import imageio
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Saving video to: {output_path}")
            
            # Save as MP4
            writer = imageio.get_writer(
                output_path,
                fps=fps,
                codec='libx264',
                quality=8,
                pixelformat='yuv420p'
            )
            
            for frame in video_frames:
                writer.append_data(frame)
            
            writer.close()
            
            logger.info(f"✓ Video saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving video: {e}")
            return False

