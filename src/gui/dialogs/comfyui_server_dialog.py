"""
ComfyUI Server Configuration Dialog

Allows users to configure and manage ComfyUI server.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QTextEdit, QGroupBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ComfyUIServerDialog(QDialog):
    """Dialog for ComfyUI server configuration and status"""
    
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    log_received = pyqtSignal(str)
    
    def __init__(self, settings, server_manager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.server_manager = server_manager
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.log_received.connect(self._append_log)
        
        self.setWindowTitle("ComfyUI Server Configuration")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self._init_ui()
        self._load_settings()
        self._update_status()
        
        # Start status updates
        self.status_timer.start(2000)  # Update every 2 seconds
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        
        # ComfyUI Path Section
        path_group = QGroupBox("ComfyUI Installation")
        path_layout = QVBoxLayout()
        
        # Path input
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Path to ComfyUI folder (e.g., D:\\ComfyUI_windows_portable\\ComfyUI)")
        self.path_input.textChanged.connect(self._on_path_changed)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_path)
        
        path_input_layout.addWidget(QLabel("ComfyUI Path:"))
        path_input_layout.addWidget(self.path_input)
        path_input_layout.addWidget(browse_btn)
        
        # Validation status
        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)
        
        path_layout.addLayout(path_input_layout)
        path_layout.addWidget(self.validation_label)
        path_group.setLayout(path_layout)
        
        # Server Status Section
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout()
        
        # Status indicator
        status_indicator_layout = QHBoxLayout()
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 16))
        self.status_label = QLabel("Checking...")
        status_indicator_layout.addWidget(self.status_indicator)
        status_indicator_layout.addWidget(self.status_label)
        status_indicator_layout.addStretch()
        
        # Server controls
        controls_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self._start_server)
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.clicked.connect(self._stop_server)
        self.stop_btn.setEnabled(False)
        
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()
        
        # Progress bar for startup
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        # Status details
        self.status_details = QTextEdit()
        self.status_details.setReadOnly(True)
        self.status_details.setMaximumHeight(100)
        
        status_layout.addLayout(status_indicator_layout)
        status_layout.addLayout(controls_layout)
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(QLabel("Details:"))
        status_layout.addWidget(self.status_details)
        status_group.setLayout(status_layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(cancel_btn)
        
        # Add all sections to main layout
        layout.addWidget(path_group)
        layout.addWidget(status_group)
        layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _load_settings(self):
        """Load settings from config"""
        comfyui_path = self.settings.get('comfyui_path', '')
        if comfyui_path:
            self.path_input.setText(comfyui_path)
    
    def _browse_path(self):
        """Browse for ComfyUI installation folder"""
        current_path = self.path_input.text()
        if not current_path:
            current_path = str(Path.home())
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select ComfyUI Installation Folder",
            current_path
        )
        
        if folder:
            self.path_input.setText(folder)
    
    def _on_path_changed(self):
        """Handle path input change"""
        path = self.path_input.text()
        if not path:
            self.validation_label.setText("")
            self.validation_label.setStyleSheet("")
            return
        
        # Update server manager path
        self.server_manager.comfyui_path = Path(path)
        
        # Validate
        is_valid, message = self.server_manager.validate_installation()
        
        if is_valid:
            self.validation_label.setText(f"✓ {message}")
            self.validation_label.setStyleSheet("color: green;")
            self.start_btn.setEnabled(True)
            # Save to settings
            self.settings.set('comfyui_path', path)
            self.settings.save()
        else:
            self.validation_label.setText(f"✗ {message}")
            self.validation_label.setStyleSheet("color: red;")
            self.start_btn.setEnabled(False)
    
    def _update_status(self):
        """Update server status display"""
        status = self.server_manager.get_status()
        
        if status['running']:
            self.status_indicator.setText("●")
            self.status_indicator.setStyleSheet("color: green;")
            self.status_label.setText(f"Running on {status['url']}")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.ok_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            
            # Show stats if available
            if 'stats' in status:
                stats = status['stats']
                details = f"Server URL: {status['url']}\n"
                details += f"System Stats: {stats}"
                self.status_details.setText(details)
            
        else:
            self.status_indicator.setText("●")
            self.status_indicator.setStyleSheet("color: red;")
            self.status_label.setText("Not running")
            self.start_btn.setEnabled(bool(self.path_input.text()))
            self.stop_btn.setEnabled(False)
            self.ok_btn.setEnabled(False)
            self.status_details.setText("Server is not running")
    
    def _start_server(self):
        """Start ComfyUI server"""
        self.progress_bar.setVisible(True)
        self.start_btn.setEnabled(False)
        self.status_label.setText("Starting server...")
        
        # Start server in background
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class StartServerThread(QThread):
            finished = pyqtSignal(bool, str)
            log_signal = pyqtSignal(str)
            
            def __init__(self, server_manager):
                super().__init__()
                self.server_manager = server_manager
            
            def run(self):
                # Pass a lambda that emits the log signal
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
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_details.setText(f"✓ {message}")
            self.server_started.emit()
        else:
            self.status_details.setText(f"✗ {message}")
            self.start_btn.setEnabled(True)
        
        self._update_status()
    
    def _stop_server(self):
        """Stop ComfyUI server"""
        self.stop_btn.setEnabled(False)
        success, message = self.server_manager.stop()
        self.status_details.append(f"\n{message}")
        
        if success:
            self.server_stopped.emit()
        
        self._update_status()
        
    def _append_log(self, line: str):
        """Append log line to details text area"""
        self.status_details.append(line)
        # Auto-scroll to bottom
        scrollbar = self.status_details.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Handle dialog close"""
        self.status_timer.stop()
        super().closeEvent(event)
