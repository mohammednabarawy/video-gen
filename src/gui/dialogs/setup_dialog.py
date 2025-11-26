"""Model setup dialog for first run"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QLineEdit, QFileDialog, QProgressBar,
    QTextEdit, QButtonGroup, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ModelSetupDialog(QDialog):
    """Dialog for setting up models on first run"""
    
    # Signal emitted when setup is complete
    setup_complete = pyqtSignal(Path, bool)  # models_path, use_comfyui
    
    def __init__(self, comfyui_manager, parent=None):
        super().__init__(parent)
        self.comfyui_manager = comfyui_manager
        self.selected_path = None
        self.use_comfyui = False
        
        self.setWindowTitle("Model Setup - First Run")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self._init_ui()
        self._check_comfyui()
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h2>Welcome to HunyuanVideo Generator!</h2>")
        layout.addWidget(title)
        
        info = QLabel(
            "This app requires ~25GB of model files to function. "
            "You can reuse existing ComfyUI models or download to a new location."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # Options group
        options_group = QGroupBox("Model Location")
        options_layout = QVBoxLayout()
        
        self.button_group = QButtonGroup()
        
        # Option 1: Use ComfyUI
        self.radio_comfyui = QRadioButton("Use existing ComfyUI models")
        self.button_group.addButton(self.radio_comfyui, 1)
        options_layout.addWidget(self.radio_comfyui)
        
        comfyui_layout = QHBoxLayout()
        comfyui_layout.addSpacing(30)
        self.comfyui_path_label = QLabel("Path:")
        self.comfyui_path_input = QLineEdit()
        self.comfyui_path_input.setReadOnly(True)
        self.comfyui_browse = QPushButton("Browse...")
        self.comfyui_browse.clicked.connect(self._browse_comfyui)
        comfyui_layout.addWidget(self.comfyui_path_label)
        comfyui_layout.addWidget(self.comfyui_path_input, 1)
        comfyui_layout.addWidget(self.comfyui_browse)
        options_layout.addLayout(comfyui_layout)
        
        options_layout.addSpacing(10)
        
        # Option 2: Download to custom location
        self.radio_custom = QRadioButton("Download to custom location")
        self.button_group.addButton(self.radio_custom, 2)
        options_layout.addWidget(self.radio_custom)
        
        custom_layout = QHBoxLayout()
        custom_layout.addSpacing(30)
        self.custom_path_label = QLabel("Path:")
        self.custom_path_input = QLineEdit()
        self.custom_browse = QPushButton("Browse...")
        self.custom_browse.clicked.connect(self._browse_custom)
        custom_layout.addWidget(self.custom_path_label)
        custom_layout.addWidget(self.custom_path_input, 1)
        custom_layout.addWidget(self.custom_browse)
        options_layout.addLayout(custom_layout)
        
        options_layout.addSpacing(10)
        
        # Option 3: Download to default
        self.radio_default = QRadioButton("Download to default location")
        self.button_group.addButton(self.radio_default, 3)
        options_layout.addWidget(self.radio_default)
        
        default_layout = QHBoxLayout()
        default_layout.addSpacing(30)
        default_path = Path.home() / ".cache" / "hunyuanvideo" / "models"
        self.default_path_label = QLabel(f"Path: {default_path}")
        self.default_path_label.setWordWrap(True)
        default_layout.addWidget(self.default_path_label)
        options_layout.addLayout(default_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        layout.addStretch()
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        self.continue_button = QPushButton("Continue")
        self.continue_button.clicked.connect(self._on_continue)
        self.continue_button.setDefault(True)
        buttons_layout.addWidget(self.continue_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _check_comfyui(self):
        """Check for existing ComfyUI installation"""
        detected_path = self.comfyui_manager.auto_detect_comfyui()
        
        if detected_path:
            self.comfyui_path_input.setText(str(detected_path))
            self.radio_comfyui.setChecked(True)
            logger.info(f"ComfyUI detected at: {detected_path}")
        else:
            # Default to default location, but keep ComfyUI option enabled for manual browse
            self.radio_default.setChecked(True)
            logger.info("ComfyUI not auto-detected, but manual browse is available")
    
    def _browse_comfyui(self):
        """Browse for ComfyUI models folder"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select ComfyUI Models Folder",
            str(Path.home())
        )
        
        if path:
            path_obj = Path(path)
            if self.comfyui_manager.is_valid_comfyui_structure(path_obj):
                self.comfyui_path_input.setText(path)
            else:
                QLabel("Invalid ComfyUI structure. Please select the 'models' directory.")
    
    def _browse_custom(self):
        """Browse for custom download location"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Custom Download Location",
            str(Path.home())
        )
        
        if path:
            self.custom_path_input.setText(path)
    
    def _on_continue(self):
        """Handle continue button"""
        selected_id = self.button_group.checkedId()
        
        if selected_id == 1:  # ComfyUI
            path_str = self.comfyui_path_input.text()
            if not path_str:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Path Required", "Please select a ComfyUI models path.")
                return
            self.selected_path = Path(path_str)
            self.use_comfyui = True
            
        elif selected_id == 2:  # Custom
            path_str = self.custom_path_input.text()
            if not path_str:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Path Required", "Please select a custom path.")
                return
            # Use path exactly as selected - assume user knows what they're doing
            # If they select a parent folder, we'll add /models
            # If they select the models folder itself, use it as-is
            selected = Path(path_str)
            
            # Check if this path already looks like a models directory
            # (has text_encoders, diffusion_models, or vae subdirectories)
            is_models_dir = any([
                (selected / 'text_encoders').exists(),
                (selected / 'diffusion_models').exists(),
                (selected / 'vae').exists()
            ])
            
            if is_models_dir:
                # User selected the models directory itself
                self.selected_path = selected
            else:
                # User selected a parent directory, add /models
                self.selected_path = selected / "models"
            
            self.use_comfyui = False
            
        else:  # Default
            self.selected_path = Path.home() / ".cache" / "hunyuanvideo" / "models"
            self.use_comfyui = False
        
        logger.info(f"Selected path: {self.selected_path}, ComfyUI: {self.use_comfyui}")
        self.setup_complete.emit(self.selected_path, self.use_comfyui)
        self.accept()
