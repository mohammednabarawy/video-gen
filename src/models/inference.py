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
    
    def __init__(self, model_manager, app_settings: Optional[AppSettings] = None, comfyui_client: Optional[ComfyUIClient] = None, comfyui_server=None):
        """
        Initialize inference wrapper
        
        Args:
            model_manager: ModelManager instance
            app_settings: AppSettings instance
            comfyui_client: ComfyUIClient instance
            comfyui_server: ComfyUIServer instance (optional)
        """
        self.model_manager = model_manager
        self.app_settings = app_settings
        self.comfyui_client = comfyui_client
        self.comfyui_server = comfyui_server
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
    
    def _validate_parameters(self, **kwargs) -> tuple[bool, str]:
        """
        Validate generation parameters to prevent server crashes
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate resolution
        width = kwargs.get('width')
        height = kwargs.get('height')
        if width and (width % 8 != 0 or height % 8 != 0):
            return False, f"Resolution must be divisible by 8 (got {width}x{height})"
            
        # Validate steps
        steps = kwargs.get('num_inference_steps', 50)
        if steps < 1 or steps > 200:
            return False, f"Steps must be between 1 and 200 (got {steps})"
            
        # Validate frames
        frames = kwargs.get('num_frames', 129)
        if frames < 1:
            return False, f"Frame count must be positive (got {frames})"
            
        return True, ""

    def _generate_with_comfyui(self, **kwargs) -> Optional[np.ndarray]:
        """Generate video using ComfyUI backend with auto-restart"""
        
        # 1. Validate parameters
        width, height = self._calculate_dimensions(
            kwargs.get('resolution', '720p'), 
            kwargs.get('aspect_ratio', '16:9')
        )
        kwargs['width'] = width
        kwargs['height'] = height
        
        is_valid, error_msg = self._validate_parameters(**kwargs)
        if not is_valid:
            logger.error(f"Invalid parameters: {error_msg}")
            return None
            
        # 2. Build workflow
        from .workflow_builder import HunyuanVideoWorkflowBuilder
        builder = HunyuanVideoWorkflowBuilder()
        
        # Enhance prompt with style and camera motion
        prompt = kwargs.get('prompt', '')
        style = kwargs.get('style')
        camera_motion = kwargs.get('camera_motion')
        
        if style or camera_motion:
            prompt = self._enhance_prompt(prompt, style, camera_motion)
            logger.info(f"Enhanced prompt for ComfyUI: {prompt}")
        
        # Determine Low VRAM mode
        low_vram = False
        if self.settings.performance_preset == PerformancePreset.LOW:
            low_vram = True
        elif self.settings.performance_preset == PerformancePreset.AUTO:
            # Check VRAM if auto
            vram_gb = self.settings.get_vram_gb()
            if vram_gb < 16:
                low_vram = True
                logger.info(f"Auto-detected Low VRAM mode ({vram_gb:.1f} GB VRAM)")

        if kwargs.get('image'):
            # Image-to-Video
            workflow = builder.build_i2v_workflow(
                prompt=prompt,
                image_path=kwargs.get('image_path'), # Pass path, not PIL image
                width=width,
                height=height,
                num_frames=kwargs.get('num_frames'),
                steps=kwargs.get('num_inference_steps'),
                cfg=kwargs.get('guidance_scale'),
                seed=kwargs.get('seed'),
                fps=kwargs.get('fps', 24),
                enable_vae_tiling=kwargs.get('enable_vae_tiling', False) or low_vram,
                low_vram=low_vram
            )
        else:
            # Text-to-Video
            workflow = builder.build_t2v_workflow(
                prompt=prompt,
                width=width,
                height=height,
                num_frames=kwargs.get('num_frames'),
                steps=kwargs.get('num_inference_steps'),
                cfg=kwargs.get('guidance_scale'),
                seed=kwargs.get('seed'),
                fps=kwargs.get('fps', 24),
                enable_vae_tiling=kwargs.get('enable_vae_tiling', False) or low_vram,
                low_vram=low_vram
            )
            
        # 3. Execute with retry/restart logic
        max_retries = 1
        oom_retry = False
        
        for attempt in range(max_retries + 2): # +1 for OOM retry
            try:
                # Check server health
                if not self.comfyui_client.is_server_running():
                    logger.warning("ComfyUI server not running, attempting start...")
                    pass

                # Connect WebSocket
                self.comfyui_client.connect()
                
                # Capture errors
                generation_error = None
                def on_error(data):
                    nonlocal generation_error
                    generation_error = data
                self.comfyui_client.register_callback('execution_error', on_error)
                
                # Register callbacks
                progress_callback = kwargs.get('progress_callback')
                preview_callback = kwargs.get('preview_callback')
                
                if progress_callback:
                    def on_progress(data):
                        value = data.get('value', 0)
                        max_value = data.get('max', 1)
                        progress_callback(value, max_value, 0)
                    self.comfyui_client.register_callback('progress', on_progress)
                    
                if preview_callback:
                    self.comfyui_client.register_callback('preview', preview_callback)
                
                # Queue prompt
                prompt_id = self.comfyui_client.queue_prompt(workflow)
                if not prompt_id:
                    raise Exception("Failed to queue prompt")
                
                # Wait for completion
                if self.comfyui_client.wait_for_completion(prompt_id):
                    # Get results
                    outputs = self.comfyui_client.get_output_images(prompt_id)
                    if outputs:
                        # Download first output
                        output = outputs[0]
                        video_data = self.comfyui_client.download_output(
                            output['filename'], 
                            output['subfolder'], 
                            output['type']
                        )
                        return video_data # Return bytes for now, or save to file
                
                # Check for OOM if failed
                if generation_error:
                    err_type = generation_error.get('exception_type', '')
                    err_msg = generation_error.get('exception_message', '')
                    
                    # Check for Windows logging error (Errno 22)
                    if 'OSError' in err_type and 'Errno 22' in err_msg:
                        logger.error("Detected Windows logging error (Errno 22) in ComfyUI")
                        logger.info("This is a known ComfyUI issue on Windows - restarting server...")
                        
                        if hasattr(self, 'comfyui_server') and self.comfyui_server:
                            # Force-stop to clear corrupted logging state
                            self.comfyui_server.restart(force_stop=True)
                            import time
                            time.sleep(3)
                            
                            # Reconnect client
                            try:
                                self.comfyui_client.connect()
                            except:
                                pass
                            
                            # Retry generation
                            continue
                        else:
                            raise RuntimeError(
                                "ComfyUI logging error detected (Errno 22). "
                                "Please manually restart ComfyUI server:\n"
                                "cd D:\\ComfyUI_windows_portable\\ComfyUI\n"
                                "..\\python_embeded\\python.exe main.py --port 8188"
                            )
                    
                    # Check for OOM
                    if 'OutOfMemoryError' in err_type or 'Allocation on device' in err_msg:
                        if not oom_retry:
                            logger.warning("OOM detected! Retrying with memory optimizations...")
                            oom_retry = True
                            
                            # Enable optimizations for next attempt
                            kwargs['enable_cpu_offload'] = True
                            kwargs['enable_vae_tiling'] = True
                            
                            # Restart server with --lowvram if it wasn't already
                            # We need to access the server manager instance. 
                            # Ideally this should be passed to inference class or accessed via singleton/app
                            # For now, we'll try to use the client to check if we can restart, 
                            # but client doesn't manage process.
                            # We need to rely on the fact that we might have access to the server object 
                            # if it was passed in __init__, or we need to signal the main app.
                            
                            # Assuming we have access to self.comfyui_server if it was passed (it wasn't in previous code)
                            # Let's check if we can access it.
                            if hasattr(self, 'comfyui_server') and self.comfyui_server:
                                logger.info("Restarting ComfyUI with --lowvram argument...")
                                self.comfyui_server.restart(args=["--lowvram"])
                                # Wait for server to come back
                                import time
                                time.sleep(10)
                                self.comfyui_client.connect()
                            
                            # Re-build basic workflow
                            if kwargs.get('image'):
                                workflow = builder.build_i2v_workflow(
                                    prompt=prompt,
                                    image_path=kwargs.get('image_path'),
                                    width=width,
                                    height=height,
                                    num_frames=kwargs.get('num_frames'),
                                    steps=kwargs.get('num_inference_steps'),
                                    cfg=kwargs.get('guidance_scale'),
                                    seed=kwargs.get('seed'),
                                    fps=kwargs.get('fps', 24),
                                    enable_vae_tiling=True
                                )
                            else:
                                workflow = builder.build_t2v_workflow(
                                    prompt=prompt,
                                    width=width,
                                    height=height,
                                    num_frames=kwargs.get('num_frames'),
                                    steps=kwargs.get('num_inference_steps'),
                                    cfg=kwargs.get('guidance_scale'),
                                    seed=kwargs.get('seed'),
                                    fps=kwargs.get('fps', 24),
                                    enable_vae_tiling=True
                                )
                                
                            # Apply memory optimizations to workflow
                            # (Already handled by builder with enable_vae_tiling=True)
                                    
                            # However, we CAN change the resolution or frame count to reduce memory.
                            logger.info("Reducing resolution and frame count to prevent OOM")
                            
                            # Aggressively reduce to 480p
                            width = 848
                            height = 480
                            kwargs['width'] = width
                            kwargs['height'] = height
                            
                            # Reduce frames significantly (to ~2 seconds)
                            # HunyuanVideo uses (frames-1)/4 latent frames, so 49 frames = 12 latent frames
                            kwargs['num_frames'] = 49 
                            
                            logger.info(f"Retrying with rescue settings: {width}x{height}, 49 frames, --lowvram, tiled VAE")
                            continue
                                
                        else:
                            logger.error("OOM persisted even after optimizations")
                            return None
                    
                    raise Exception(f"Generation failed: {err_msg}")
                
                break # Success
                
            except Exception as e:
                logger.error(f"Generation failed (attempt {attempt+1}): {e}")
                
                if attempt < max_retries and not oom_retry:
                    logger.info("Attempting to restart ComfyUI server...")
                    import time
                    time.sleep(5)
                elif not oom_retry: # Don't return if we are about to OOM retry
                    pass
                else:
                    # If we already OOM retried or max retries reached
                    if attempt >= max_retries + 1:
                         return None
            finally:
                self.comfyui_client.disconnect()
                
        return None
            
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
