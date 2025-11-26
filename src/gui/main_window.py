"""Main application window"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTextEdit, QFileDialog, QMessageBox, QGroupBox, QButtonGroup,
    QRadioButton, QLineEdit, QSlider, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QAction, QKeySequence
from pathlib import Path
import json
import logging

from .widgets.preview_widget import PreviewWidget
from .widgets.preset_library import PresetLibraryWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""
    
    # Signal for video generation request
    generation_requested = pyqtSignal(str, dict)  # prompt, params
    preview_updated = pyqtSignal(bytes, str)  # image_data, format
    
    def __init__(self, settings, inference_engine, app_settings=None, server_manager=None):
        super().__init__()
        self.settings = settings  # Legacy settings
        self.app_settings = app_settings  # New AppSettings
        self.server_manager = server_manager
        self.inference_engine = inference_engine
        
        self.setWindowTitle("HunyuanVideo 1.5 Generator")
        self.resize(
            self.settings.get('window_width', 900),
            self.settings.get('window_height', 800)
        )
        
        self._init_menu_bar()
        self._init_ui()
        self._load_presets()
        self._init_ui()
        self._load_presets()
        self._connect_signals()
        self._apply_app_settings()
        
        # Connect preview signal
        self.preview_updated.connect(self.preview_widget.update_preview)
    
    def _init_menu_bar(self):
        """Initialize menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(settings_action)
        
        edit_menu.addSeparator()
        
        server_action = QAction("Configure &Server...", self)
        server_action.triggered.connect(self._show_server_config)
        edit_menu.addAction(server_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        docs_action.triggered.connect(self._show_documentation)
        help_menu.addAction(docs_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout: controls on left, preview on right
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Left side: all controls
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, 2)  # 2/3 of width
        
        # Right side: preview
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 1)  # 1/3 of width
        
        # Mode selection
        mode_group = QGroupBox("Mode")
        mode_layout = QHBoxLayout()
        
        self.mode_group = QButtonGroup()
        self.radio_t2v = QRadioButton("Text-to-Video")
        self.radio_i2v = QRadioButton("Image-to-Video")
        self.mode_group.addButton(self.radio_t2v, 0)
        self.mode_group.addButton(self.radio_i2v, 1)
        self.radio_t2v.setChecked(True)
        
        mode_layout.addWidget(self.radio_t2v)
        mode_layout.addWidget(self.radio_i2v)
        mode_layout.addStretch()
        
        mode_group.setLayout(mode_layout)
        left_layout.addWidget(mode_group)
        
        # Prompt section
        prompt_group = QGroupBox("Prompt")
        prompt_layout = QVBoxLayout()
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText(
            "Describe the video you want to generate...\n\n"
            "Example: A golden retriever running on a beach at sunset, "
            "cinematic lighting, 4K quality"
        )
        self.prompt_text.setMinimumHeight(100)
        prompt_layout.addWidget(self.prompt_text)
        
        # Prompt enhancements
        prompt_options_layout = QHBoxLayout()
        
        self.enable_prompt_rewrite = QCheckBox("Enable prompt rewriting (AI enhancement)")
        prompt_options_layout.addWidget(self.enable_prompt_rewrite)
        
        prompt_options_layout.addStretch()
        
        prompt_options_layout.addStretch()
        
        # Preset button (toggles library)
        self.preset_btn = QPushButton("Visual Presets")
        self.preset_btn.setCheckable(True)
        self.preset_btn.clicked.connect(self._toggle_preset_library)
        prompt_options_layout.addWidget(self.preset_btn)
        
        prompt_layout.addLayout(prompt_options_layout)
        
        prompt_group.setLayout(prompt_layout)
        left_layout.addWidget(prompt_group)
        
        # Image input (for I2V)
        self.image_group = QGroupBox("Image Input")
        image_layout = QHBoxLayout()
        
        self.image_path_input = QLineEdit()
        self.image_path_input.setReadOnly(True)
        self.image_path_input.setPlaceholderText("No image selected")
        image_layout.addWidget(self.image_path_input, 1)
        
        self.browse_image_btn = QPushButton("Browse...")
        self.browse_image_btn.clicked.connect(self._browse_image)
        image_layout.addWidget(self.browse_image_btn)
        
        self.image_group.setLayout(image_layout)
        self.image_group.setVisible(False)  # Hidden by default
        left_layout.addWidget(self.image_group)
        
        # Basic controls
        controls_group = QGroupBox("Settings")
        controls_layout = QVBoxLayout()
        
        # Row 1: Resolution and Duration
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(['480p', '720p', '1080p'])
        self.resolution_combo.setCurrentText(self.settings.get('default_resolution', '720p'))
        row1.addWidget(self.resolution_combo)
        
        row1.addSpacing(20)
        
        row1.addWidget(QLabel("Duration (seconds):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(2, 10)
        self.duration_spin.setValue(self.settings.get('default_duration', 5))
        row1.addWidget(self.duration_spin)
        
        row1.addStretch()
        controls_layout.addLayout(row1)
        
        # Row 2: Aspect Ratio and FPS
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("Aspect Ratio:"))
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(['16:9', '9:16', '1:1', '4:3', '21:9'])
        self.aspect_ratio_combo.setCurrentText(self.settings.get('default_aspect_ratio', '16:9'))
        row2.addWidget(self.aspect_ratio_combo)
        
        row2.addSpacing(20)
        
        row2.addWidget(QLabel("FPS:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(['8', '16', '24', '25', '30'])
        self.fps_combo.setCurrentText(str(self.settings.get('default_fps', 25)))
        row2.addWidget(self.fps_combo)
        
        row2.addStretch()
        controls_layout.addLayout(row2)
        
        # Row 3: Style and Seed
        row3 = QHBoxLayout()
        
        row3.addWidget(QLabel("Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            'None', 'Cinematic', 'Realistic', 'Anime', '3D', 'Artistic'
        ])
        self.style_combo.setCurrentText(self.settings.get('default_style', 'Cinematic'))
        row3.addWidget(self.style_combo)
        
        row3.addSpacing(20)
        
        row3.addWidget(QLabel("Seed:"))
        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText("Random")
        self.seed_input.setMaximumWidth(100)
        row3.addWidget(self.seed_input)
        
        self.random_seed_check = QCheckBox("Random")
        self.random_seed_check.setChecked(True)
        row3.addWidget(self.random_seed_check)
        
        row3.addStretch()
        controls_layout.addLayout(row3)
        
        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)
        
        # Advanced options (collapsible)
        self.advanced_group = QGroupBox("Advanced Options")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        advanced_layout = QVBoxLayout()
        
        # CFG Scale
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("CFG Scale:"))
        self.cfg_slider = QSlider(Qt.Orientation.Horizontal)
        self.cfg_slider.setRange(10, 150)  # 1.0 to 15.0
        self.cfg_slider.setValue(int(self.settings.get('default_cfg_scale', 7.0) * 10))
        self.cfg_value_label = QLabel(f"{self.cfg_slider.value() / 10:.1f}")
        self.cfg_slider.valueChanged.connect(
            lambda v: self.cfg_value_label.setText(f"{v / 10:.1f}")
        )
        cfg_layout.addWidget(self.cfg_slider)
        cfg_layout.addWidget(self.cfg_value_label)
        advanced_layout.addLayout(cfg_layout)
        
        # Camera Motion
        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Camera Motion:"))
        self.camera_combo = QComboBox()
        self.camera_combo.addItems([
            'None', 'static', 'zoom_in', 'zoom_out', 'pan_left',
            'pan_right', 'tilt_up', 'tilt_down', 'orbit', 'dynamic'
        ])
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addStretch()
        advanced_layout.addLayout(camera_layout)
        
        # Inference Steps
        steps_layout = QHBoxLayout()
        steps_layout.addWidget(QLabel("Inference Steps:"))
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 100)
        self.steps_spin.setValue(self.settings.get('default_inference_steps', 50))
        steps_layout.addWidget(self.steps_spin)
        steps_layout.addStretch()
        advanced_layout.addLayout(steps_layout)
        
        # Options
        self.enable_sr_check = QCheckBox("Enable Super-Resolution (upscale to 1080p)")
        self.enable_sr_check.setChecked(self.settings.get('enable_super_resolution', False))
        advanced_layout.addWidget(self.enable_sr_check)
        
        self.enable_cpu_offload_check = QCheckBox("Enable CPU Offloading (<24GB VRAM)")
        self.enable_cpu_offload_check.setChecked(self.settings.get('enable_cpu_offload', False))
        advanced_layout.addWidget(self.enable_cpu_offload_check)
        
        self.enable_vae_tiling_check = QCheckBox("Enable VAE Tiling (reduce VRAM)")
        self.enable_vae_tiling_check.setChecked(self.settings.get('enable_vae_tiling', False))
        advanced_layout.addWidget(self.enable_vae_tiling_check)
        
        self.advanced_group.setLayout(advanced_layout)
        left_layout.addWidget(self.advanced_group)
        
        # Output section
        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout()
        
        output_layout.addWidget(QLabel("Save to:"))
        
        self.output_path_input = QLineEdit()
        default_output = self.settings.get('default_output_dir')
        if default_output:
            self.output_path_input.setText(str(Path(default_output) / "video.mp4"))
        else:
            self.output_path_input.setText(
                str(Path.home() / "Videos" / "HunyuanVideo" / "video.mp4")
            )
        output_layout.addWidget(self.output_path_input, 1)
        
        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.browse_output_btn)
        
        output_group.setLayout(output_layout)
        left_layout.addWidget(output_group)
        
        # Generate button
        self.generate_btn = QPushButton("Generate Video")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold; }"
        )
        self.generate_btn.clicked.connect(self._on_generate)
        left_layout.addWidget(self.generate_btn)
        
        # Progress section
        self.progress_group = QGroupBox("Progress")
        self.progress_group.setVisible(False)
        progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_label)
        
        from PyQt6.QtWidgets import QProgressBar as PBar
        self.progress_bar = PBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        progress_layout.addWidget(self.cancel_btn)
        
        self.progress_group.setLayout(progress_layout)
        left_layout.addWidget(self.progress_group)
        
        left_layout.addStretch()
        
        # Preview area
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_widget = PreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group, 1)  # Give it stretch factor
        
        # Preset Library (Dock-like behavior)
        self.preset_library = PresetLibraryWidget()
        self.preset_library.setVisible(False)
        self.preset_library.preset_selected.connect(self._on_preset_selected)
        
        # Add preset library to left side below other controls
        left_layout.addWidget(self.preset_library)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _connect_signals(self):
        """Connect signals"""
        # Mode change
        self.radio_t2v.toggled.connect(self._on_mode_changed)
        self.radio_i2v.toggled.connect(self._on_mode_changed)
        
        # Random seed checkbox
        self.random_seed_check.toggled.connect(
            lambda checked: self.seed_input.setEnabled(not checked)
        )
    
    def _on_mode_changed(self):
        """Handle mode change"""
        is_i2v = self.radio_i2v.isChecked()
        self.image_group.setVisible(is_i2v)
    
    def _load_presets(self):
        """Load presets from file"""
        # Presets are now loaded by the PresetLibraryWidget
        pass
    
    def _toggle_preset_library(self):
        """Toggle preset library visibility"""
        visible = self.preset_btn.isChecked()
        self.preset_library.setVisible(visible)
    
    def _on_preset_selected(self, preset_data):
        """Handle preset selection"""
        if preset_data:
            self.prompt_text.setPlainText(preset_data.get('prompt', ''))
            self.style_combo.setCurrentText(preset_data.get('style', 'None'))
            self.duration_spin.setValue(preset_data.get('duration', 5))
            self.resolution_combo.setCurrentText(preset_data.get('resolution', '720p'))
            
            camera_motion = preset_data.get('camera_motion')
            if camera_motion:
                self.camera_combo.setCurrentText(camera_motion)
                
            # Hide library after selection
            self.preset_btn.setChecked(False)
            self.preset_library.setVisible(False)
    
    def _browse_image(self):
        """Browse for input image"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        
        if path:
            self.image_path_input.setText(path)
    
    def _browse_output(self):
        """Browse for output location"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Video As",
            self.output_path_input.text(),
            "MP4 Video (*.mp4);;All Files (*)"
        )
        
        if path:
            self.output_path_input.setText(path)
    
    def _on_generate(self):
        """Handle generate button click"""
        # Validate inputs
        prompt = self.prompt_text.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Input Required", "Please enter a prompt.")
            return
        
        # Check image for I2V mode
        is_i2v = self.radio_i2v.isChecked()
        if is_i2v and not self.image_path_input.text():
            QMessageBox.warning(self, "Input Required", "Please select an input image for I2V mode.")
            return
        
        # Collect parameters
        params = {
            'image_path': self.image_path_input.text() if is_i2v else None,
            'resolution': self.resolution_combo.currentText(),
            'aspect_ratio': self.aspect_ratio_combo.currentText(),
            'duration': self.duration_spin.value(),
            'fps': int(self.fps_combo.currentText()),
            'style': self.style_combo.currentText() if self.style_combo.currentText() != 'None' else None,
            'camera_motion': self.camera_combo.currentText() if self.camera_combo.currentText() != 'None' else None,
            'seed': int(self.seed_input.text()) if self.seed_input.text() and not self.random_seed_check.isChecked() else None,
            'cfg_scale': self.cfg_slider.value() / 10.0,
            'inference_steps': self.steps_spin.value(),
            'enable_prompt_rewriting': self.enable_prompt_rewrite.isChecked(),
            'enable_super_resolution': self.enable_sr_check.isChecked(),
            'enable_cpu_offload': self.enable_cpu_offload_check.isChecked(),
            'enable_vae_tiling': self.enable_vae_tiling_check.isChecked(),
            'output_path': self.output_path_input.text()
        }
        
        # Save prompt to history
        self.settings.add_recent_prompt(prompt)
        
        # Emit signal
        self.generation_requested.emit(prompt, params)
    
    def _on_cancel(self):
        """Handle cancel button"""
        # This will be connected to worker cancel
        pass
    
    def set_generating(self, generating: bool):
        """Update UI for generation state"""
        self.generate_btn.setEnabled(not generating)
        self.progress_group.setVisible(generating)
        
        if generating:
            self.statusBar().showMessage("Generating video...")
        else:
            self.statusBar().showMessage("Ready")
    
    def update_progress(self, step: int, total: int, status: str):
        """Update progress display"""
        progress = int((step / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)
        self.progress_label.setText(status)
    
    def closeEvent(self, event):
        """Handle window close"""
        # Save window size
        self.settings.set('window_width', self.width())
        self.settings.set('window_height', self.height())
        self.settings.save()
        
        event.accept()
    
    def _apply_app_settings(self):
        """Apply settings from AppSettings to UI"""
        if not self.app_settings:
            return
        
        # Apply default values from app settings
        self.resolution_combo.setCurrentText(self.app_settings.default_resolution)
        self.aspect_ratio_combo.setCurrentText(self.app_settings.default_aspect_ratio)
        self.duration_spin.setValue(self.app_settings.default_duration)
        self.fps_combo.setCurrentText(str(self.app_settings.default_fps))
        self.style_combo.setCurrentText(self.app_settings.default_style)
        self.cfg_slider.setValue(int(self.app_settings.default_cfg_scale * 10))
        self.steps_spin.setValue(self.app_settings.default_inference_steps)
        self.enable_prompt_rewrite.setChecked(self.app_settings.enable_prompt_rewriting)
        self.enable_sr_check.setChecked(self.app_settings.enable_super_resolution)
        self.enable_cpu_offload_check.setChecked(self.app_settings.enable_cpu_offload)
        self.enable_vae_tiling_check.setChecked(self.app_settings.enable_vae_tiling)
        
        # Show/hide advanced options based on settings
        self.advanced_group.setChecked(self.app_settings.show_advanced_options)
    
    def _on_new(self):
        """Handle New action"""
        # Clear all inputs
        self.prompt_text.clear()
        self.image_path_input.clear()
        self.seed_input.clear()
        self.random_seed_check.setChecked(True)
        self.radio_t2v.setChecked(True)
        self._apply_app_settings()
    
    def _show_settings(self):
        """Show settings dialog"""
        if not self.app_settings or not self.server_manager:
            QMessageBox.information(
                self,
                "Settings",
                "Settings system is not initialized. Please restart the application."
            )
            return
        
        from .dialogs.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.app_settings, self.server_manager, self, initial_tab=0)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
    
    def _show_server_config(self):
        """Show server configuration dialog"""
        if not self.server_manager:
            QMessageBox.information(
                self,
                "Server Configuration",
                "Server manager is not initialized. Please restart the application."
            )
            return
        
        from .dialogs.settings_dialog import SettingsDialog
        
        # Open settings with Connection tab (index 0)
        dialog = SettingsDialog(self.app_settings, self.server_manager, self, initial_tab=0)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
    
    def _show_documentation(self):
        """Show documentation"""
        import webbrowser
        docs_path = Path(__file__).parent.parent.parent / "README.md"
        if docs_path.exists():
            webbrowser.open(docs_path.as_uri())
        else:
            QMessageBox.information(
                self,
                "Documentation",
                "Documentation not found. Please check the README.md file."
            )
    
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About HunyuanVideo Generator",
            "<h2>HunyuanVideo 1.5 Generator</h2>"
            "<p>A professional video generation application powered by HunyuanVideo 1.5</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Text-to-Video generation</li>"
            "<li>Image-to-Video generation</li>"
            "<li>ComfyUI integration</li>"
            "<li>Advanced performance settings</li>"
            "</ul>"
            "<p><b>Version:</b> 1.0.0</p>"
            "<p><b>Based on:</b> Tencent HunyuanVideo 1.5</p>"
            "<p><b>Inspired by:</b> Krita AI Diffusion</p>"
        )
    
    def _on_settings_changed(self):
        """Handle settings change"""
        # Reload settings from app_settings
        self._apply_app_settings()
        self.statusBar().showMessage("Settings applied", 3000)
