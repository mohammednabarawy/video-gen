"""Main application entry point"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import Qt

# Import application modules
from config.settings import Settings
from config.app_settings import AppSettings
from config.comfyui_compat import ComfyUIPathManager
from config.paths import PathManager
from models.downloader import ModelDownloader
from models.model_manager import ModelManager
from models.inference import HunyuanVideoInference
from models.comfyui_server import ComfyUIServer
from models.comfyui_client import ComfyUIClient
from gui.main_window import MainWindow
from gui.dialogs.setup_dialog import ModelSetupDialog
from gui.dialogs.download_dialog import DownloadProgressDialog
from gui.dialogs.comfyui_server_dialog import ComfyUIServerDialog
from utils.logger import setup_logger
from utils.async_worker import VideoGenerationWorker, ModelDownloadWorker
from utils.video_utils import VideoUtils

# Setup logging
logger = setup_logger('hunyuan_video')


class Application:
    """Main application class"""
    
    def __init__(self):
        """Initialize application"""
        logger.info("="* 60)
        logger.info("HunyuanVideo 1.5 Generator Starting...")
        logger.info("="* 60)
        
        # Initialize Qt application
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("HunyuanVideo Generator")
        
        # Connect cleanup handler
        self.qt_app.aboutToQuit.connect(self._cleanup)
        
        # Initialize components
        self.settings = Settings()  # Legacy settings
        self.app_settings = AppSettings()  # New comprehensive settings
        self.path_manager = PathManager()
        self.comfyui_manager = ComfyUIPathManager()
        
        # ComfyUI server components
        comfyui_path = self.app_settings.comfyui_path or self.settings.get('comfyui_path', '')
        self.comfyui_server = ComfyUIServer(comfyui_path) if comfyui_path else ComfyUIServer('')
        # Ensure server URL has protocol
        server_url = self.app_settings.server_url
        if not server_url.startswith(('http://', 'https://')):
            server_url = f"http://{server_url}"
        self.comfyui_client = ComfyUIClient(server_url)
        
        self.downloader = None
        self.model_manager = None
        self.inference_engine = None
        self.main_window = None
        
        self.generation_worker = None
    
    def run(self):
        """Run the application"""
        try:
            # Step 1: Setup models path (optional - can be configured later)
            
            # Step 3: Show main window
            logger.info("Launching main window...")
            self.main_window = MainWindow(
                self.settings,
                self.inference_engine,
                self.app_settings,
                self.comfyui_server
            )
            
            # Connect signals
            if self.inference_engine:
                self.main_window.generation_requested.connect(self._on_generation_requested)
            
            self.main_window.show()
            
            # Show settings dialog on first run
            if not self.app_settings.comfyui_path:
                logger.info("First run detected - showing settings dialog")
                QMessageBox.information(
                    self.main_window,
                    "Welcome to HunyuanVideo Generator",
                    "Welcome! Please configure your ComfyUI server in the settings dialog.\n\n"
                    "You can access settings anytime from Edit → Settings (Ctrl+,)"
                )
                # Show settings dialog
                from gui.dialogs.settings_dialog import SettingsDialog
                settings_dialog = SettingsDialog(
                    self.app_settings,
                    self.comfyui_server,
                    self.main_window
                )
                settings_dialog.exec()
            
            logger.info("Application ready!")
            
            # Run Qt event loop
            return self.qt_app.exec()
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            QMessageBox.critical(
                None,
                "Fatal Error",
                f"An error occurred:\n\n{str(e)}\n\nCheck logs for details."
            )
            return 1
    
    def _setup_models_path_optional(self) -> Path:
        """
        Setup models path (optional - can be skipped)
        
        Returns:
            Path to models directory or None if skipped
        """
        # Check if already configured
        configured_path = self.settings.get_models_path()
        
        if configured_path and configured_path.exists():
            logger.info(f"Using configured models path: {configured_path}")
            return configured_path
        
        # Not configured - can be set up later
        return None
    
    def _setup_models_path(self) -> Path:
        """
        Setup models path (first run or reconfigure)
        
        Returns:
            Path to models directory or None if cancelled
        """
        # Check if already configured
        configured_path = self.settings.get_models_path()
        
        if configured_path and configured_path.exists():
            logger.info(f"Using configured models path: {configured_path}")
            return configured_path
        
        # First run - show setup dialog
        logger.info("First run detected - showing setup dialog")
        
        setup_dialog = ModelSetupDialog(self.comfyui_manager)
        
        if setup_dialog.exec():
            selected_path = setup_dialog.selected_path
            use_comfyui = setup_dialog.use_comfyui
            
            # Save configuration
            self.settings.set_models_path(selected_path, use_comfyui)
            logger.info(f"Models path configured: {selected_path} (ComfyUI: {use_comfyui})")
            
            return selected_path
        else:
            return None
    
    def _ensure_models_ready(self, models_path: Path) -> bool:
        """
        Ensure all required models are downloaded
        
        Args:
            models_path: Path where models should be stored
            
        Returns:
            True if models are ready
        """
        logger.info("Checking models...")
        
        # Initialize downloader
        self.downloader = ModelDownloader(models_path)
        
        # Check if models are ready
        if self.downloader.is_ready():
            logger.info("All required models are ready!")
            return True
        
        # Models need to be downloaded
        missing = self.downloader.get_missing_models(include_optional=False)
        total_size = sum(m['size_gb'] for m in missing)
        
        logger.info(f"Missing {len(missing)} models, total size: {total_size:.1f} GB")
        
        # Ask user to confirm download
        reply = QMessageBox.question(
            None,
            "Download Required",
            f"The following models need to be downloaded:\n\n"
            f"• {len(missing)} model file(s)\n"
            f"• Total size: {total_size:.1f} GB\n"
            f"• Location: {models_path}\n\n"
            "This may take some time depending on your internet connection.\n\n"
            "Proceed with download?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return False
        
        # Download models with progress dialog
        return self._download_models()
    
    def _download_models(self) -> bool:
        """
        Download models with progress dialog
        
        Returns:
            True if download successful
        """
        # Create progress dialog
        progress_dialog = DownloadProgressDialog()
        
        # Create download worker
        download_worker = ModelDownloadWorker(
            self.downloader,
            include_optional=False
        )
        
        # Connect signals
        download_worker.status_updated.connect(progress_dialog.update_status)
        download_worker.download_progress.connect(progress_dialog.update_file_progress)
        download_worker.download_complete.connect(
            lambda success: progress_dialog.set_complete(success)
        )
        download_worker.download_failed.connect(
            lambda error: progress_dialog.set_complete(False)
        )
        
        # Start download
        download_worker.start()
        
        # Show dialog (blocks until closed)
        result = progress_dialog.exec()
        
        # Wait for worker to finish
        download_worker.wait()
        
        # Check if successful
        return self.downloader.is_ready()
    
    def _on_generation_requested(self, prompt: str, params: dict):
        """
        Handle video generation request
        
        Args:
            prompt: User prompt
            params: Generation parameters
        """
        logger.info("Generation requested")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Params: {params}")
        
        # Update UI
        self.main_window.set_generating(True)
        
        # Prepare generation parameters
        from PIL import Image
        
        gen_params = {
            'resolution': params['resolution'],
            'aspect_ratio': params['aspect_ratio'],
            'num_frames': params['duration'] * params['fps'],
            'fps': params['fps'],
            'guidance_scale': params['cfg_scale'],
            'num_inference_steps': params['inference_steps'],
            'seed': params.get('seed'),
            'style': params.get('style'),
            'camera_motion': params.get('camera_motion'),
            'enable_prompt_rewriting': params['enable_prompt_rewriting'],
            'enable_cpu_offload': params['enable_cpu_offload'],
            'enable_vae_tiling': params['enable_vae_tiling'],
        }
        
        # Load image for I2V if provided
        if params.get('image_path'):
            try:
                image = Image.open(params['image_path'])
                gen_params['image'] = image
                logger.info(f"Loaded input image: {params['image_path']}")
            except Exception as e:
                logger.error(f"Error loading image: {e}")
                QMessageBox.critical(
                    self.main_window,
                    "Error",
                    f"Failed to load image:\n{str(e)}"
                )
                self.main_window.set_generating(False)
                return
        
        # Create worker
        self.generation_worker = VideoGenerationWorker(
            self.inference_engine,
            prompt,
            gen_params,
            self.main_window
        )
        
        # Connect signals
        self.generation_worker.progress_updated.connect(
            self.main_window.update_progress
        )
        self.generation_worker.generation_complete.connect(
            lambda frames: self._on_generation_complete(frames, params)
        )
        self.generation_worker.generation_failed.connect(
            self._on_generation_failed
        )
        
        # Connect cancel button
        self.main_window.cancel_btn.clicked.connect(
            self.generation_worker.cancel
        )
        
        # Start generation
        self.generation_worker.start()
    
    def _on_generation_complete(self, video_frames, params: dict):
        """Handle successful generation"""
        logger.info("Generation complete!")
        
        # Save video
        output_path = Path(params['output_path'])
        fps = params['fps']
        
        try:
            success = VideoUtils.save_video(
                video_frames,
                output_path,
                fps=fps
            )
            
            if success:
                QMessageBox.information(
                    self.main_window,
                    "Success",
                    f"Video saved successfully!\n\nLocation: {output_path}"
                )
            else:
                QMessageBox.warning(
                    self.main_window,
                    "Warning",
                    "Video generation completed, but failed to save file."
                )
                
        except Exception as e:
            logger.error(f"Error saving video: {e}")
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Failed to save video:\n{str(e)}"
            )
        
        finally:
            self.main_window.set_generating(False)
    
    def _on_generation_failed(self, error_message: str):
        """Handle failed generation"""
        logger.error(f"Generation failed: {error_message}")
        
        QMessageBox.critical(
            self.main_window,
            "Generation Failed",
            f"Video generation failed:\n\n{error_message}"
        )
        
        self.main_window.set_generating(False)
    
    def _cleanup(self):
        """Cleanup resources before application exit"""
        logger.info("Cleaning up before exit...")
        
        # Stop ComfyUI server if running
        if self.comfyui_server and self.comfyui_server.process:
            logger.info("Stopping ComfyUI server...")
            success, message = self.comfyui_server.stop()
            if success:
                logger.info("ComfyUI server stopped successfully")
            else:
                logger.warning(f"Failed to stop ComfyUI server: {message}")
        
        # Cancel any running generation
        if self.generation_worker and self.generation_worker.isRunning():
            logger.info("Cancelling running generation...")
            self.generation_worker.cancel()
            self.generation_worker.wait(timeout=2000)


def main():
    """Application entry point"""
    app = Application()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
