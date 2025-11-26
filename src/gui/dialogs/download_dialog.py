"""Download progress dialog"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class DownloadProgressDialog(QDialog):
    """Dialog showing model download progress"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Models")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h3>Downloading Models</h3>")
        layout.addWidget(title)
        
        # Status label
        self.status_label = QLabel("Preparing download...")
        layout.addWidget(self.status_label)
        
        # Overall progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Current file label
        self.file_label = QLabel("")
        layout.addWidget(self.file_label)
        
        # File progress
        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        self.file_progress.setValue(0)
        layout.addWidget(self.file_progress)
        
        # Log/details
        log_label = QLabel("Details:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        layout.addStretch()
        
        # Close button (initially disabled)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_status(self, status: str):
        """Update status message"""
        self.status_label.setText(status)
        self.add_log(status)
    
    def update_overall_progress(self, value: int):
        """Update overall progress bar"""
        self.progress_bar.setValue(value)
    
    def update_file_progress(self, filename: str, progress: float):
        """Update file download progress"""
        if progress < 0:  # Error
            self.file_label.setText(f"❌ Error downloading: {filename}")
            self.file_progress.setValue(0)
        elif progress >= 100:
            self.file_label.setText(f"✓ Downloaded: {filename}")
            self.file_progress.setValue(100)
        else:
            self.file_label.setText(f"Downloading: {filename}")
            self.file_progress.setValue(int(progress))
    
    def add_log(self, message: str):
        """Add message to log"""
        self.log_text.append(message)
    
    def set_complete(self, success: bool):
        """Mark download as complete"""
        self.close_button.setEnabled(True)
        
        if success:
            self.status_label.setText("✓ All models downloaded successfully!")
            self.progress_bar.setValue(100)
        else:
            self.status_label.setText("❌ Download failed or incomplete")
