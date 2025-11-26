"""
ComfyUI Custom Node Manager

Automatically detects and installs required custom nodes for HunyuanVideo.
Inspired by Pinokio's one-click automation philosophy.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NodeManager:
    """Manages ComfyUI custom nodes with automatic installation"""
    
    # Required nodes for HunyuanVideo workflows
    REQUIRED_NODES = {
        "ComfyUI-HunyuanVideoWrapper": {
            "url": "https://github.com/kijai/ComfyUI-HunyuanVideoWrapper.git",
            "description": "HunyuanVideo model support for ComfyUI"
        },
        "ComfyUI-VideoHelperSuite": {
            "url": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
            "description": "Video saving and preview nodes"
        }
    }
    
    def __init__(self, comfyui_path: Path):
        """
        Initialize NodeManager
        
        Args:
            comfyui_path: Path to ComfyUI installation
        """
        self.comfyui_path = Path(comfyui_path)
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        
    def check_missing_nodes(self) -> List[str]:
        """
        Check which required nodes are missing
        
        Returns:
            List of missing node names
        """
        if not self.custom_nodes_path.exists():
            logger.warning(f"Custom nodes directory not found: {self.custom_nodes_path}")
            return list(self.REQUIRED_NODES.keys())
        
        missing = []
        for node_name in self.REQUIRED_NODES:
            node_path = self.custom_nodes_path / node_name
            if not node_path.exists():
                logger.info(f"Missing node: {node_name}")
                missing.append(node_name)
            else:
                logger.debug(f"Found node: {node_name}")
        
        return missing
    
    def install_node(
        self, 
        node_name: str, 
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """
        Install a custom node via git clone
        
        Args:
            node_name: Name of the node to install
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, message)
        """
        if node_name not in self.REQUIRED_NODES:
            return False, f"Unknown node: {node_name}"
        
        node_info = self.REQUIRED_NODES[node_name]
        repo_url = node_info["url"]
        target_path = self.custom_nodes_path / node_name
        
        try:
            # Create custom_nodes directory if it doesn't exist
            self.custom_nodes_path.mkdir(parents=True, exist_ok=True)
            
            # Clone repository
            logger.info(f"Cloning {node_name} from {repo_url}...")
            if progress_callback:
                progress_callback(f"Cloning {node_name}...")
            
            result = subprocess.run(
                ["git", "clone", repo_url, str(target_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = f"Git clone failed: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
            
            logger.info(f"Successfully cloned {node_name}")
            
            # Install Python dependencies if requirements.txt exists
            requirements_path = target_path / "requirements.txt"
            if requirements_path.exists():
                logger.info(f"Installing dependencies for {node_name}...")
                if progress_callback:
                    progress_callback(f"Installing dependencies for {node_name}...")
                
                success, msg = self._install_requirements(target_path)
                if not success:
                    return False, f"Node cloned but dependency installation failed: {msg}"
            
            return True, f"Successfully installed {node_name}"
            
        except subprocess.TimeoutExpired:
            return False, "Installation timed out (>5 minutes)"
        except Exception as e:
            logger.error(f"Error installing {node_name}: {e}", exc_info=True)
            return False, f"Installation error: {str(e)}"
    
    def _install_requirements(self, node_path: Path) -> Tuple[bool, str]:
        """
        Install requirements.txt for a node
        
        Args:
            node_path: Path to the node directory
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Determine correct Python executable
            # Try to use ComfyUI's Python (portable or venv)
            import sys
            python_exe = sys.executable
            
            # Check for portable installation
            portable_python = self.comfyui_path.parent / "python_embeded" / "python.exe"
            if portable_python.exists():
                python_exe = str(portable_python)
            else:
                # Check for venv
                venv_python = self.comfyui_path / "venv" / "Scripts" / "python.exe"
                if venv_python.exists():
                    python_exe = str(venv_python)
            
            logger.info(f"Using Python: {python_exe}")
            
            # Install requirements
            result = subprocess.run(
                [python_exe, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=str(node_path),
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for pip install
            )
            
            if result.returncode != 0:
                error_msg = f"Pip install failed: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
            
            logger.info("Dependencies installed successfully")
            return True, "Dependencies installed"
            
        except subprocess.TimeoutExpired:
            return False, "Dependency installation timed out (>10 minutes)"
        except Exception as e:
            logger.error(f"Error installing requirements: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def install_all_missing(
        self, 
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """
        Install all missing required nodes
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, message)
        """
        missing = self.check_missing_nodes()
        
        if not missing:
            return True, "All required nodes are already installed"
        
        logger.info(f"Installing {len(missing)} missing nodes: {missing}")
        
        failed = []
        for node_name in missing:
            success, msg = self.install_node(node_name, progress_callback)
            if not success:
                failed.append((node_name, msg))
                logger.error(f"Failed to install {node_name}: {msg}")
        
        if failed:
            error_details = "\n".join([f"- {name}: {msg}" for name, msg in failed])
            return False, f"Failed to install {len(failed)} node(s):\n{error_details}"
        
        return True, f"Successfully installed {len(missing)} node(s)"
    
    def verify_installation(self) -> Tuple[bool, List[str]]:
        """
        Verify that all required nodes are installed
        
        Returns:
            Tuple of (all_installed, missing_nodes)
        """
        missing = self.check_missing_nodes()
        return (len(missing) == 0, missing)
