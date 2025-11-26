"""
Settings Dialog

Comprehensive settings dialog with tabs for Connection, Models, Performance, and Advanced settings.
Inspired by Krita AI Diffusion's settings UI.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QFileDialog,
    QTextEdit, QProgressBar, QSlider, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path
import logging

from config.app_settings import (
    AppSettings, ServerMode, ServerBackend, PerformancePreset, VideoFormat
)
from models.comfyui_server import ComfyUIServer

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Comprehensive settings dialog"""
    
    settings_changed = pyqtSignal()
    log_received = pyqtSignal(str)
    
    def __init__(self, settings: AppSettings, server_manager: ComfyUIServer, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        self.settings = settings
        self.server_manager = server_manager
        self.initial_tab = initial_tab
        
        self.setWindowTitle("Settings - HunyuanVideo Generator")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        
        self._init_ui()
        self._load_settings()
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_server_status)
        self.status_timer.start(2000)
        
        self.log_received.connect(self._append_log)
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.tabs.addTab(self._create_connection_tab(), "Connection")
        self.tabs.addTab(self._create_models_tab(), "Models")
        self.tabs.addTab(self._create_generation_tab(), "Generation")
        self.tabs.addTab(self._create_performance_tab(), "Performance")
        self.tabs.addTab(self._create_advanced_tab(), "Advanced")
        
        self.tabs.setCurrentIndex(self.initial_tab)
        
        layout.addWidget(self.tabs)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._apply_settings)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _create_connection_tab(self) -> QWidget:
        """Create Connection tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Server Mode
        mode_group = QGroupBox("Server Management")
        mode_layout = QVBoxLayout()
        
        mode_label = QLabel("To generate videos, the app connects to a ComfyUI server:")
        mode_label.setWordWrap(True)
        mode_layout.addWidget(mode_label)
        
        self.server_mode_combo = QComboBox()
        self.server_mode_combo.addItem("Managed by this application", ServerMode.MANAGED)
        self.server_mode_combo.addItem("Connect to external server", ServerMode.EXTERNAL)
        self.server_mode_combo.currentIndexChanged.connect(self._on_server_mode_changed)
        mode_layout.addWidget(self.server_mode_combo)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Managed Server Settings
        self.managed_group = QGroupBox("Managed Server Settings")
        managed_layout = QFormLayout()
        
        # ComfyUI Path
        comfyui_path_layout = QHBoxLayout()
        self.comfyui_path_input = QLineEdit()
        self.comfyui_path_input.setPlaceholderText("Path to ComfyUI installation")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_comfyui_path)
        comfyui_path_layout.addWidget(self.comfyui_path_input)
        comfyui_path_layout.addWidget(browse_btn)
        managed_layout.addRow("ComfyUI Path:", comfyui_path_layout)
        
        # Validation status
        self.path_validation_label = QLabel()
        self.path_validation_label.setWordWrap(True)
        managed_layout.addRow("", self.path_validation_label)
        
        # Backend
        self.backend_combo = QComboBox()
        for backend in ServerBackend.supported():
            self.backend_combo.addItem(backend.value[0], backend)
        managed_layout.addRow("Backend:", self.backend_combo)
        
        # Server Arguments
        self.server_args_input = QLineEdit()
        self.server_args_input.setPlaceholderText("Additional command line arguments")
        managed_layout.addRow("Server Arguments:", self.server_args_input)
        
        # Auto-start
        self.auto_start_checkbox = QCheckBox("Automatically start server on application launch")
        managed_layout.addRow("", self.auto_start_checkbox)
        
        self.managed_group.setLayout(managed_layout)
        layout.addWidget(self.managed_group)
        
        # External Server Settings
        self.external_group = QGroupBox("External Server Settings")
        external_layout = QFormLayout()
        
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("127.0.0.1:8188")
        external_layout.addRow("Server URL:", self.server_url_input)
        
        self.external_group.setLayout(external_layout)
        layout.addWidget(self.external_group)
        
        # Server Status
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()
        
        status_indicator_layout = QHBoxLayout()
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 16))
        self.status_label = QLabel("Checking...")
        status_indicator_layout.addWidget(self.status_indicator)
        status_indicator_layout.addWidget(self.status_label)
        status_indicator_layout.addStretch()
        
        status_layout.addLayout(status_indicator_layout)
        
        # Server controls
        controls_layout = QHBoxLayout()
        self.start_server_btn = QPushButton("Start Server")
        self.start_server_btn.clicked.connect(self._start_server)
        self.stop_server_btn = QPushButton("Stop Server")
        self.stop_server_btn.clicked.connect(self._stop_server)
        controls_layout.addWidget(self.start_server_btn)
        controls_layout.addWidget(self.stop_server_btn)
        controls_layout.addStretch()
        
        status_layout.addLayout(controls_layout)
        
        # Server Logs (Collapsible)
        self.logs_group = QGroupBox("Server Logs")
        self.logs_group.setCheckable(True)
        self.logs_group.setChecked(False)
        logs_layout = QVBoxLayout()
        
        self.server_logs = QTextEdit()
        self.server_logs.setReadOnly(True)
        self.server_logs.setMinimumHeight(150)
        self.server_logs.setStyleSheet("font-family: Consolas, monospace; font-size: 10px;")
        logs_layout.addWidget(self.server_logs)
        
        self.logs_group.setLayout(logs_layout)
        status_layout.addWidget(self.logs_group)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_models_tab(self) -> QWidget:
        """Create Models tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Models Path
        path_group = QGroupBox("Models Location")
        path_layout = QFormLayout()
        
        models_path_layout = QHBoxLayout()
        self.models_path_input = QLineEdit()
        browse_models_btn = QPushButton("Browse...")
        browse_models_btn.clicked.connect(self._browse_models_path)
        models_path_layout.addWidget(self.models_path_input)
        models_path_layout.addWidget(browse_models_btn)
        path_layout.addRow("Models Path:", models_path_layout)
        
        self.use_comfyui_models_checkbox = QCheckBox("Use ComfyUI models directory")
        path_layout.addRow("", self.use_comfyui_models_checkbox)
        
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # Model Management
        management_group = QGroupBox("Model Management")
        management_layout = QVBoxLayout()
        
        self.auto_download_checkbox = QCheckBox("Automatically download missing models")
        self.check_on_startup_checkbox = QCheckBox("Check for missing models on startup")
        
        management_layout.addWidget(self.auto_download_checkbox)
        management_layout.addWidget(self.check_on_startup_checkbox)
        
        # Model status
        status_text = QTextEdit()
        status_text.setReadOnly(True)
        status_text.setMaximumHeight(150)
        status_text.setPlaceholderText("Model status will be displayed here...")
        management_layout.addWidget(QLabel("Model Status:"))
        management_layout.addWidget(status_text)
        
        # Check models button
        check_btn = QPushButton("Check Models Now")
        check_btn.clicked.connect(self._check_models)
        management_layout.addWidget(check_btn)
        
        management_group.setLayout(management_layout)
        layout.addWidget(management_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_generation_tab(self) -> QWidget:
        """Create Generation tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Default Generation Settings
        defaults_group = QGroupBox("Default Generation Settings")
        defaults_layout = QFormLayout()
        
        # Resolution
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["480p", "720p", "1080p"])
        defaults_layout.addRow("Resolution:", self.resolution_combo)
        
        # Aspect Ratio
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(["16:9", "9:16", "1:1", "4:3", "21:9"])
        defaults_layout.addRow("Aspect Ratio:", self.aspect_ratio_combo)
        
        # Duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 10)
        self.duration_spin.setSuffix(" seconds")
        defaults_layout.addRow("Duration:", self.duration_spin)
        
        # FPS
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setValue(25)
        defaults_layout.addRow("FPS:", self.fps_spin)
        
        # Style
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Cinematic", "Anime", "Realistic", "Artistic", "Documentary"])
        defaults_layout.addRow("Style:", self.style_combo)
        
        # CFG Scale
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 20.0)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setValue(7.0)
        defaults_layout.addRow("CFG Scale:", self.cfg_spin)
        
        # Inference Steps
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 100)
        self.steps_spin.setValue(50)
        defaults_layout.addRow("Inference Steps:", self.steps_spin)
        
        defaults_group.setLayout(defaults_layout)
        layout.addWidget(defaults_group)
        
        # Output Settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()
        
        # Video Format
        self.format_combo = QComboBox()
        for fmt in VideoFormat:
            self.format_combo.addItem(fmt.value, fmt)
        output_layout.addRow("Video Format:", self.format_combo)
        
        # Quality
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(0, 51)
        self.quality_slider.setValue(23)
        self.quality_slider.setInvertedAppearance(True)  # Lower CRF = better quality
        self.quality_label = QLabel("23 (Good)")
        self.quality_slider.valueChanged.connect(self._update_quality_label)
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        output_layout.addRow("Quality:", quality_layout)
        
        # Save Metadata
        self.save_metadata_checkbox = QCheckBox("Save generation metadata in video file")
        output_layout.addRow("", self.save_metadata_checkbox)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_performance_tab(self) -> QWidget:
        """Create Performance tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Performance Preset
        preset_group = QGroupBox("Performance Preset")
        preset_layout = QVBoxLayout()
        
        preset_label = QLabel("Configures performance settings to match available hardware:")
        preset_label.setWordWrap(True)
        preset_layout.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        for preset in PerformancePreset:
            self.preset_combo.addItem(preset.value.title(), preset)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Custom Performance Settings
        self.custom_group = QGroupBox("Custom Performance Settings")
        custom_layout = QVBoxLayout()
        
        self.cpu_offload_checkbox = QCheckBox("Enable CPU Offloading")
        self.cpu_offload_checkbox.setToolTip("Offload model components to CPU to save VRAM")
        custom_layout.addWidget(self.cpu_offload_checkbox)
        
        self.vae_tiling_checkbox = QCheckBox("Enable VAE Tiling")
        self.vae_tiling_checkbox.setToolTip("Process video in tiles to reduce VRAM usage")
        custom_layout.addWidget(self.vae_tiling_checkbox)
        
        self.xformers_checkbox = QCheckBox("Enable xFormers Memory Efficient Attention")
        self.xformers_checkbox.setToolTip("Use optimized attention implementation (requires xformers)")
        custom_layout.addWidget(self.xformers_checkbox)
        
        self.custom_group.setLayout(custom_layout)
        layout.addWidget(self.custom_group)
        
        # VRAM Info
        info_group = QGroupBox("System Information")
        info_layout = QVBoxLayout()
        
        self.vram_label = QLabel("Detecting...")
        info_layout.addWidget(self.vram_label)
        self._update_vram_info()
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Create Advanced tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Advanced Features
        features_group = QGroupBox("Advanced Features")
        features_layout = QVBoxLayout()
        
        self.prompt_rewriting_checkbox = QCheckBox("Enable Prompt Rewriting")
        self.prompt_rewriting_checkbox.setToolTip("Use LLM to enhance prompts")
        features_layout.addWidget(self.prompt_rewriting_checkbox)
        
        self.super_resolution_checkbox = QCheckBox("Enable Super Resolution")
        self.super_resolution_checkbox.setToolTip("Upscale output to 1080p")
        features_layout.addWidget(self.super_resolution_checkbox)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # UI Settings
        ui_group = QGroupBox("User Interface")
        ui_layout = QVBoxLayout()
        
        self.show_advanced_checkbox = QCheckBox("Show advanced options in main window")
        ui_layout.addWidget(self.show_advanced_checkbox)
        
        self.confirm_generation_checkbox = QCheckBox("Confirm before starting generation")
        ui_layout.addWidget(self.confirm_generation_checkbox)
        
        self.auto_open_checkbox = QCheckBox("Automatically open output video when complete")
        ui_layout.addWidget(self.auto_open_checkbox)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # Debug Settings
        debug_group = QGroupBox("Debug")
        debug_layout = QFormLayout()
        
        self.debug_checkbox = QCheckBox("Enable debug mode")
        debug_layout.addRow("", self.debug_checkbox)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        debug_layout.addRow("Log Level:", self.log_level_combo)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _load_settings(self):
        """Load current settings into UI"""
        # Connection
        mode_index = self.server_mode_combo.findData(self.settings.server_mode)
        if mode_index >= 0:
            self.server_mode_combo.setCurrentIndex(mode_index)
        
        self.comfyui_path_input.setText(self.settings.comfyui_path)
        self.server_url_input.setText(self.settings.server_url)
        
        backend_index = self.backend_combo.findData(self.settings.server_backend)
        if backend_index >= 0:
            self.backend_combo.setCurrentIndex(backend_index)
        
        self.server_args_input.setText(self.settings.server_arguments)
        self.auto_start_checkbox.setChecked(self.settings.auto_start_server)
        
        # Models
        self.models_path_input.setText(self.settings.models_path)
        self.use_comfyui_models_checkbox.setChecked(self.settings.use_comfyui_models)
        self.auto_download_checkbox.setChecked(self.settings.auto_download_models)
        self.check_on_startup_checkbox.setChecked(self.settings.check_models_on_startup)
        
        # Generation
        self.resolution_combo.setCurrentText(self.settings.default_resolution)
        self.aspect_ratio_combo.setCurrentText(self.settings.default_aspect_ratio)
        self.duration_spin.setValue(self.settings.default_duration)
        self.fps_spin.setValue(self.settings.default_fps)
        self.style_combo.setCurrentText(self.settings.default_style)
        self.cfg_spin.setValue(self.settings.default_cfg_scale)
        self.steps_spin.setValue(self.settings.default_inference_steps)
        
        format_index = self.format_combo.findData(self.settings.default_output_format)
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)
        
        self.quality_slider.setValue(self.settings.output_quality)
        self.save_metadata_checkbox.setChecked(self.settings.save_metadata)
        
        # Performance
        preset_index = self.preset_combo.findData(self.settings.performance_preset)
        if preset_index >= 0:
            self.preset_combo.setCurrentIndex(preset_index)
        
        self.cpu_offload_checkbox.setChecked(self.settings.enable_cpu_offload)
        self.vae_tiling_checkbox.setChecked(self.settings.enable_vae_tiling)
        self.xformers_checkbox.setChecked(self.settings.enable_xformers)
        
        # Advanced
        self.prompt_rewriting_checkbox.setChecked(self.settings.enable_prompt_rewriting)
        self.super_resolution_checkbox.setChecked(self.settings.enable_super_resolution)
        self.show_advanced_checkbox.setChecked(self.settings.show_advanced_options)
        self.confirm_generation_checkbox.setChecked(self.settings.confirm_before_generation)
        self.auto_open_checkbox.setChecked(self.settings.auto_open_output)
        self.debug_checkbox.setChecked(self.settings.debug_mode)
        self.log_level_combo.setCurrentText(self.settings.log_level)
        
        self._on_server_mode_changed()
        self._update_server_status()
    
    def _apply_settings(self):
        """Apply settings from UI to settings object"""
        # Connection
        self.settings.server_mode = self.server_mode_combo.currentData()
        self.settings.comfyui_path = self.comfyui_path_input.text()
        self.settings.server_url = self.server_url_input.text()
        self.settings.server_backend = self.backend_combo.currentData()
        self.settings.server_arguments = self.server_args_input.text()
        self.settings.auto_start_server = self.auto_start_checkbox.isChecked()
        
        # Models
        self.settings.models_path = self.models_path_input.text()
        self.settings.use_comfyui_models = self.use_comfyui_models_checkbox.isChecked()
        self.settings.auto_download_models = self.auto_download_checkbox.isChecked()
        self.settings.check_models_on_startup = self.check_on_startup_checkbox.isChecked()
        
        # Generation
        self.settings.default_resolution = self.resolution_combo.currentText()
        self.settings.default_aspect_ratio = self.aspect_ratio_combo.currentText()
        self.settings.default_duration = self.duration_spin.value()
        self.settings.default_fps = self.fps_spin.value()
        self.settings.default_style = self.style_combo.currentText()
        self.settings.default_cfg_scale = self.cfg_spin.value()
        self.settings.default_inference_steps = self.steps_spin.value()
        self.settings.default_output_format = self.format_combo.currentData()
        self.settings.output_quality = self.quality_slider.value()
        self.settings.save_metadata = self.save_metadata_checkbox.isChecked()
        
        # Performance
        self.settings.performance_preset = self.preset_combo.currentData()
        self.settings.enable_cpu_offload = self.cpu_offload_checkbox.isChecked()
        self.settings.enable_vae_tiling = self.vae_tiling_checkbox.isChecked()
        self.settings.enable_xformers = self.xformers_checkbox.isChecked()
        
        # Advanced
        self.settings.enable_prompt_rewriting = self.prompt_rewriting_checkbox.isChecked()
        self.settings.enable_super_resolution = self.super_resolution_checkbox.isChecked()
        self.settings.show_advanced_options = self.show_advanced_checkbox.isChecked()
        self.settings.confirm_before_generation = self.confirm_generation_checkbox.isChecked()
        self.settings.auto_open_output = self.auto_open_checkbox.isChecked()
        self.settings.debug_mode = self.debug_checkbox.isChecked()
        self.settings.log_level = self.log_level_combo.currentText()
        
        # Save to file
        self.settings.save()
        
        self.settings_changed.emit()
        
        QMessageBox.information(self, "Settings Applied", "Settings have been saved successfully.")
    
    def _on_server_mode_changed(self):
        """Handle server mode change"""
        mode = self.server_mode_combo.currentData()
        self.managed_group.setVisible(mode == ServerMode.MANAGED)
        self.external_group.setVisible(mode == ServerMode.EXTERNAL)
    
    def _on_preset_changed(self):
        """Handle performance preset change"""
        preset = self.preset_combo.currentData()
        is_custom = preset == PerformancePreset.CUSTOM
        self.custom_group.setEnabled(is_custom)
        
        if not is_custom:
            # Apply preset
            self.settings.apply_performance_preset(preset)
            self.cpu_offload_checkbox.setChecked(self.settings.enable_cpu_offload)
            self.vae_tiling_checkbox.setChecked(self.settings.enable_vae_tiling)
    
    def _browse_comfyui_path(self):
        """Browse for ComfyUI installation"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select ComfyUI Installation Folder",
            self.comfyui_path_input.text() or str(Path.home())
        )
        if path:
            self.comfyui_path_input.setText(path)
            self._validate_comfyui_path()
    
    def _browse_models_path(self):
        """Browse for models directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Models Directory",
            self.models_path_input.text() or str(Path.home())
        )
        if path:
            self.models_path_input.setText(path)
    
    def _validate_comfyui_path(self):
        """Validate ComfyUI path"""
        path = self.comfyui_path_input.text()
        if not path:
            self.path_validation_label.setText("")
            return
        
        self.server_manager.comfyui_path = Path(path)
        is_valid, message = self.server_manager.validate_installation()
        
        if is_valid:
            self.path_validation_label.setText(f"✓ {message}")
            self.path_validation_label.setStyleSheet("color: green;")
        else:
            self.path_validation_label.setText(f"✗ {message}")
            self.path_validation_label.setStyleSheet("color: red;")
    
    def _update_server_status(self):
        """Update server status display"""
        is_running = self.server_manager.is_running()
        
        if is_running:
            self.status_indicator.setText("●")
            self.status_indicator.setStyleSheet("color: green;")
            self.status_label.setText(f"Running on {self.server_manager.server_url}")
            self.start_server_btn.setEnabled(False)
            self.stop_server_btn.setEnabled(True)
        else:
            self.status_indicator.setText("●")
            self.status_indicator.setStyleSheet("color: red;")
            self.status_label.setText("Not running")
            self.start_server_btn.setEnabled(True)
            self.stop_server_btn.setEnabled(False)
    
    def _start_server(self):
        """Start ComfyUI server"""
        self.start_server_btn.setEnabled(False)
        self.status_label.setText("Starting server...")
        self.logs_group.setChecked(True)
        self.server_logs.clear()
        self.server_logs.append("Starting ComfyUI server...")
        
        # Start server in background
        from PyQt6.QtCore import QThread
        
        class StartServerThread(QThread):
            finished = pyqtSignal(bool, str)
            log_signal = pyqtSignal(str)
            
            def __init__(self, server_manager):
                super().__init__()
                self.server_manager = server_manager
            
            def run(self):
                success, message = self.server_manager.start(
                    timeout=60,
                    log_callback=lambda line: self.log_signal.emit(line)
                )
                self.finished.emit(success, message)
        
        self.start_thread = StartServerThread(self.server_manager)
        self.start_thread.finished.connect(self._on_server_started)
        self.start_thread.log_signal.connect(self.log_received)
        self.start_thread.start()
    
    def _on_server_started(self, success: bool, message: str):
        """Handle server start completion"""
        if success:
            QMessageBox.information(self, "Server Started", message)
            self.server_logs.append(f"\nSUCCESS: {message}")
        else:
            QMessageBox.warning(self, "Server Start Failed", message)
            self.server_logs.append(f"\nFAILED: {message}")
            self.start_server_btn.setEnabled(True)
        
        self._update_server_status()
    
    def _stop_server(self):
        """Stop ComfyUI server"""
        success, message = self.server_manager.stop()
        if success:
            QMessageBox.information(self, "Server Stopped", message)
        else:
            QMessageBox.warning(self, "Server Stop Failed", message)
        self._update_server_status()
    
    def _check_models(self):
        """Check model status"""
        QMessageBox.information(self, "Check Models", "Model checking not yet implemented.")
    
    def _update_quality_label(self, value):
        """Update quality label"""
        if value < 18:
            quality_text = "Excellent"
        elif value < 23:
            quality_text = "Very Good"
        elif value < 28:
            quality_text = "Good"
        else:
            quality_text = "Fair"
        self.quality_label.setText(f"{value} ({quality_text})")
    
    def _update_vram_info(self):
        """Update VRAM information"""
        try:
            import torch
            if torch.cuda.is_available():
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                gpu_name = torch.cuda.get_device_name(0)
                self.vram_label.setText(f"GPU: {gpu_name}\nVRAM: {vram_gb:.1f} GB")
            else:
                self.vram_label.setText("No CUDA GPU detected")
        except:
            self.vram_label.setText("Unable to detect GPU")
    
    def accept(self):
        """Override accept to apply settings"""
        self._apply_settings()
        super().accept()
    
    def closeEvent(self, event):
        """Handle dialog close"""
        self.status_timer.stop()
        super().closeEvent(event)

    def _append_log(self, line: str):
        """Append log line to logs text area"""
        self.server_logs.append(line)
        # Auto-scroll to bottom
        scrollbar = self.server_logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
