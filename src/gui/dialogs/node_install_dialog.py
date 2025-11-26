"""
Node Installation Dialog

Prompts user to install missing ComfyUI custom nodes.
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QProgressBar, QHBoxLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from models.node_manager import NodeManager

logger = logging.getLogger(__name__)


class NodeInstallWorker(QThread):
    """Worker thread for installing nodes"""
    
    progress_updated = pyqtSignal(str)
    installation_complete = pyqtSignal(bool, str)
    
    def __init__(self, node_manager: NodeManager):
        super().__init__()
        self.node_manager = node_manager
    
    def run(self):
        """Install all missing nodes"""
        try:
            def progress_callback(message):
                self.progress_updated.emit(message)
            
            success, message = self.node_manager.install_all_missing(progress_callback)
            self.installation_complete.emit(success, message)
            
        except Exception as e:
            logger.error(f"Installation error: {e}", exc_info=True)
            self.installation_complete.emit(False, f"Error: {str(e)}")


class NodeInstallDialog(QDialog):
    """Dialog to prompt and install missing ComfyUI nodes"""
    
    def __init__(self, comfyui_path: Path, parent=None):
        super().__init__(parent)
        self.comfyui_path = comfyui_path
        self.node_manager = NodeManager(comfyui_path)
        self.install_worker = None
        
        self.setWindowTitle("Install Required Custom Nodes")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self._init_ui()
        self._check_nodes()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h2>Missing Custom Nodes</h2>")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "ComfyUI requires custom nodes to run HunyuanVideo workflows.\n"
            "The following nodes are missing and need to be installed:"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Missing nodes group
        self.nodes_group = QGroupBox("Required Nodes")
        nodes_layout = QVBoxLayout()
        self.nodes_list = QTextEdit()
        self.nodes_list.setReadOnly(True)
        self.nodes_list.setMaximumHeight(150)
        nodes_layout.addWidget(self.nodes_list)
        self.nodes_group.setLayout(nodes_layout)
        layout.addWidget(self.nodes_group)
        
        # Installation info
        info = QLabel(
            "<b>Installation Process:</b><br>"
            "• Nodes will be cloned from GitHub<br>"
            "• Python dependencies will be installed automatically<br>"
            "• ComfyUI must be restarted after installation"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Progress section
        self.progress_label = QLabel("")
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.hide()
        layout.addWidget(self.log_output)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.install_button = QPushButton("Install Now")
        self.install_button.clicked.connect(self._start_installation)
        self.install_button.setDefault(True)
        button_layout.addWidget(self.install_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _check_nodes(self):
        """Check which nodes are missing"""
        missing = self.node_manager.check_missing_nodes()
        
        if not missing:
            self.nodes_list.setPlainText("All required nodes are already installed!")
            self.install_button.setEnabled(False)
            return
        
        # Display missing nodes
        node_text = ""
        for node_name in missing:
            node_info = NodeManager.REQUIRED_NODES.get(node_name, {})
            desc = node_info.get("description", "No description")
            node_text += f"• {node_name}\n  {desc}\n\n"
        
        self.nodes_list.setPlainText(node_text)
    
    def _start_installation(self):
        """Start the installation process"""
        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_label.setText("Installing nodes...")
        self.progress_label.show()
        self.progress_bar.show()
        self.log_output.show()
        
        # Create and start worker thread
        self.install_worker = NodeInstallWorker(self.node_manager)
        self.install_worker.progress_updated.connect(self._on_progress)
        self.install_worker.installation_complete.connect(self._on_complete)
        self.install_worker.start()
    
    def _on_progress(self, message: str):
        """Handle progress updates"""
        self.progress_label.setText(message)
        self.log_output.append(f"• {message}")
    
    def _on_complete(self, success: bool, message: str):
        """Handle installation completion"""
        self.progress_bar.hide()
        
        if success:
            self.progress_label.setText("✓ Installation complete!")
            self.log_output.append(f"\n<b>Success:</b> {message}")
            self.install_button.setText("Close")
            self.install_button.setEnabled(True)
            self.install_button.clicked.disconnect()
            self.install_button.clicked.connect(self.accept)
        else:
            self.progress_label.setText("✗ Installation failed")
            self.log_output.append(f"\n<b>Error:</b> {message}")
            self.cancel_button.setEnabled(True)
