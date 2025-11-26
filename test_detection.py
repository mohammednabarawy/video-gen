"""Test script to check ComfyUI model detection"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.comfyui_compat import ComfyUIPathManager
from models.downloader import ModelDownloader
from utils.logger import setup_logger

# Setup logging
logger = setup_logger('test_detection')

def test_comfyui_detection(path_str: str):
    """Test ComfyUI detection for a given path"""
    logger.info("="*60)
    logger.info("Testing ComfyUI Model Detection")
    logger.info("="*60)
    
    path = Path(path_str)
    logger.info(f"Testing path: {path}")
    
    # Test ComfyUI manager
    logger.info("\n1. Testing ComfyUI Path Manager...")
    comfyui_manager = ComfyUIPathManager(path)
    is_valid = comfyui_manager.is_valid_comfyui_structure(path)
    logger.info(f"Result: {'VALID' if is_valid else 'INVALID'}")
    
    if is_valid:
        # Test downloader
        logger.info("\n2. Testing Model Downloader...")
        downloader = ModelDownloader(path)
        
        logger.info("\n3. Checking existing models...")
        existing = downloader.check_existing_models()
        
        logger.info("\n4. Summary:")
        for category, files in existing.items():
            found = sum(1 for exists in files.values() if exists)
            total = len(files)
            logger.info(f"  {category}: {found}/{total} models found")
        
        logger.info("\n5. Missing models:")
        missing = downloader.get_missing_models(include_optional=True)
        if missing:
            for model in missing:
                logger.info(f"  - {model['name']} ({model['size_gb']} GB) - {model['category']}")
        else:
            logger.info("  None - all models present!")
        
        logger.info("\n6. Model readiness:")
        is_ready = downloader.is_ready()
        logger.info(f"  Ready for inference: {'YES' if is_ready else 'NO'}")
    
    logger.info("\n" + "="*60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        # Default test path
        test_path = r"D:\ComfyUI_windows_portable\ComfyUI\models"
        logger.info(f"No path provided, using default: {test_path}")
    
    test_comfyui_detection(test_path)
