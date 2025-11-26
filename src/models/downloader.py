"""Model downloader with ComfyUI compatibility"""

from pathlib import Path
from typing import Optional, Callable, Dict, List
from huggingface_hub import hf_hub_download
import logging

logger = logging.getLogger(__name__)


class ModelDownloader:
    """Downloads and manages HunyuanVideo model files"""
    
    # HuggingFace repository
    REPO_ID = "Comfy-Org/HunyuanVideo_1.5_repackaged"
    
    # Model files to download
    MODEL_FILES = {
        'text_encoders': [
            {
                'name': 'qwen_2.5_vl_7b_fp8_scaled.safetensors',
                'path': 'split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors',
                'size_gb': 7.5,
                'required': True
            },
            {
                'name': 'byt5_small_glyphxl_fp16.safetensors',
                'path': 'split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors',
                'size_gb': 0.5,
                'required': False  # Optional for text rendering
            }
        ],
        'diffusion_models': [
            {
                'name': 'hunyuanvideo1.5_720p_t2v_fp16.safetensors',
                'path': 'split_files/diffusion_models/hunyuanvideo1.5_720p_t2v_fp16.safetensors',
                'size_gb': 16.0,
                'required': True
            },
            {
                'name': 'hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors',
                'path': 'split_files/diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors',
                'size_gb': 8.0,
                'required': False  # Optional for super-resolution
            }
        ],
        'vae': [
            {
                'name': 'hunyuanvideo15_vae_fp16.safetensors',
                'path': 'split_files/vae/hunyuanvideo15_vae_fp16.safetensors',
                'size_gb': 1.0,
                'required': True
            }
        ]
    }
    
    def __init__(
        self, 
        models_base_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Initialize model downloader
        
        Args:
            models_base_path: Base path for models (ComfyUI-compatible structure)
            progress_callback: Callback function(filename, progress_percent)
        """
        self.models_base_path = Path(models_base_path) if models_base_path else \
                                Path.home() / ".cache" / "hunyuanvideo" / "models"
        self.progress_callback = progress_callback
        
        # ComfyUI-compatible folder structure
        self.text_encoders_path = self.models_base_path / "text_encoders"
        self.diffusion_models_path = self.models_base_path / "diffusion_models"
        self.vae_path = self.models_base_path / "vae"
    
    def check_existing_models(self) -> Dict[str, Dict[str, bool]]:
        """
        Check which models already exist (skip download)
        
        Returns:
            Dictionary of {category: {filename: exists}}
        """
        existing = {
            'text_encoders': {},
            'diffusion_models': {},
            'vae': {}
        }
        
        logger.info("Checking for existing models...")
        logger.info(f"Base path: {self.models_base_path}")
        
        for category, files in self.MODEL_FILES.items():
            category_path = getattr(self, f"{category}_path")
            
            # Log the directory we're checking
            logger.info(f"Checking {category} in: {category_path}")
            
            # List all files in this directory if it exists
            if category_path.exists():
                actual_files = list(category_path.glob("*.safetensors"))
                logger.info(f"Found {len(actual_files)} .safetensors files in {category}:")
                for f in actual_files:
                    logger.info(f"  - {f.name} ({f.stat().st_size / (1024**3):.2f} GB)")
            else:
                logger.warning(f"Directory does not exist: {category_path}")
                actual_files = []
            
            # Check each required file
            for file_info in files:
                filename = file_info['name']
                file_path = category_path / filename
                exists = file_path.exists()
                
                # If exact match not found, check for similar files
                if not exists and actual_files:
                    # Try to find a similar file (e.g., different precision variant)
                    base_name = filename.replace('_fp16', '').replace('_bf16', '').replace('_fp8_scaled', '')
                    similar_files = [
                        f for f in actual_files 
                        if base_name.split('.')[0].lower() in f.name.lower()
                    ]
                    
                    if similar_files:
                        # Use the first similar file found
                        similar_file = similar_files[0]
                        logger.info(f"✓ Found similar model for {filename}: {similar_file.name}")
                        exists = True
                        # Optionally create a symlink or note the actual path
                
                existing[category][filename] = exists
                
                if exists:
                    logger.info(f"✓ Found existing model: {file_path}")
                else:
                    logger.info(f"✗ Missing model: {filename}")
        
        return existing
    
    def get_missing_models(self, include_optional: bool = False) -> List[Dict]:
        """
        Get list of models that need to be downloaded
        
        Args:
            include_optional: Whether to include optional models
            
        Returns:
            List of model info dictionaries for missing models
        """
        existing = self.check_existing_models()
        missing = []
        
        for category, files in self.MODEL_FILES.items():
            for file_info in files:
                filename = file_info['name']
                is_required = file_info['required']
                
                # Skip if already exists
                if existing[category].get(filename, False):
                    continue
                
                # Include if required or if including optional
                if is_required or include_optional:
                    missing.append({
                        **file_info,
                        'category': category
                    })
        
        return missing
    
    def calculate_download_size(self, include_optional: bool = False) -> float:
        """
        Calculate total download size in GB
        
        Args:
            include_optional: Whether to include optional models
            
        Returns:
            Total size in GB
        """
        missing = self.get_missing_models(include_optional)
        return sum(model['size_gb'] for model in missing)
    
    def create_directories(self) -> None:
        """Create ComfyUI folder structure"""
        self.text_encoders_path.mkdir(parents=True, exist_ok=True)
        self.diffusion_models_path.mkdir(parents=True, exist_ok=True)
        self.vae_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created model directories at: {self.models_base_path}")
    
    def download_model(
        self, 
        category: str, 
        file_info: Dict
    ) -> Optional[Path]:
        """
        Download a single model file
        
        Args:
            category: Model category (text_encoders, diffusion_models, vae)
            file_info: Model file information dictionary
            
        Returns:
            Path to downloaded file or None if failed
        """
        filename = file_info['name']
        repo_path = file_info['path']
        
        logger.info(f"Downloading {filename}...")
        
        try:
            # Download to ComfyUI-compatible directory
            category_path = getattr(self, f"{category}_path")
            
            # Report progress
            if self.progress_callback:
                self.progress_callback(filename, 0.0)
            
            # Download from HuggingFace
            downloaded_path = hf_hub_download(
                repo_id=self.REPO_ID,
                filename=repo_path,
                local_dir=self.models_base_path.parent,
                local_dir_use_symlinks=False
            )
            
            # Move to correct location if needed
            target_path = category_path / filename
            downloaded_file = Path(downloaded_path)
            
            if downloaded_file != target_path:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                downloaded_file.rename(target_path)
                logger.info(f"Moved to: {target_path}")
            
            if self.progress_callback:
                self.progress_callback(filename, 100.0)
            
            logger.info(f"✓ Downloaded: {filename}")
            return target_path
            
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            if self.progress_callback:
                self.progress_callback(filename, -1.0)  # Signal error
            return None
    
    def download_all_models(self, include_optional: bool = False) -> bool:
        """
        Download all missing models
        
        Args:
            include_optional: Whether to download optional models
            
        Returns:
            True if all required models are available, False otherwise
        """
        logger.info("Starting model download...")
        
        # Create directories
        self.create_directories()
        
        # Get missing models
        missing = self.get_missing_models(include_optional)
        
        if not missing:
            logger.info("All required models already downloaded!")
            return True
        
        # Report download size
        total_size = sum(m['size_gb'] for m in missing)
        logger.info(f"Will download {len(missing)} model(s), total size: {total_size:.1f} GB")
        
        # Download each missing model
        success_count = 0
        for model_info in missing:
            category = model_info['category']
            result = self.download_model(category, model_info)
            if result:
                success_count += 1
        
        logger.info(f"Downloaded {success_count}/{len(missing)} models")
        
        # Check if all required models are now available
        return self.is_ready()
    
    def is_ready(self) -> bool:
        """
        Check if all required models are available
        
        Returns:
            True if all required models exist
        """
        existing = self.check_existing_models()
        
        for category, files in self.MODEL_FILES.items():
            for file_info in files:
                if file_info['required']:
                    filename = file_info['name']
                    if not existing[category].get(filename, False):
                        logger.warning(f"Missing required model: {filename}")
                        return False
        
        logger.info("All required models are ready!")
        return True
    
    def get_model_info(self) -> Dict:
        """
        Get information about available models
        
        Returns:
            Dictionary with model status information
        """
        existing = self.check_existing_models()
        missing = self.get_missing_models(include_optional=True)
        
        return {
            'ready': self.is_ready(),
            'existing': existing,
            'missing_count': len(missing),
            'total_size_gb': self.calculate_download_size(include_optional=True),
            'models_path': str(self.models_base_path)
        }
