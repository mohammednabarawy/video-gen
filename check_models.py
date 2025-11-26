"""Simple diagnostic script to check ComfyUI models"""

import sys
from pathlib import Path

def check_comfyui_path(path_str: str):
    """Check what's in the ComfyUI models directory"""
    path = Path(path_str)
    
    print(f"Checking path: {path}")
    print(f"Path exists: {path.exists()}")
    print()
    
    if not path.exists():
        print("ERROR: Path does not exist!")
        return
    
    # Check subdirectories
    subdirs = ['text_encoders', 'diffusion_models', 'vae', 'unet', 'checkpoints', 'clip']
    
    print("Subdirectories:")
    for subdir in subdirs:
        subdir_path = path / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob("*.safetensors"))
            print(f"  ✓ {subdir}/")
            print(f"    Files: {len(files)}")
            for f in files[:5]:  # Show first 5
                size_gb = f.stat().st_size / (1024**3)
                print(f"      - {f.name} ({size_gb:.2f} GB)")
            if len(files) > 5:
                print(f"      ... and {len(files) - 5} more")
        else:
            print(f"  ✗ {subdir}/ (not found)")
    
    print("\nDone!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_comfyui_path(sys.argv[1])
    else:
        print("Usage: python check_models.py <path_to_comfyui_models>")
        print("Example: python check_models.py 'D:\\ComfyUI_windows_portable\\ComfyUI\\models'")
