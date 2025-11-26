"""
Preview widget for displaying generated videos and real-time previews
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QPixmap, QImage
import logging

logger = logging.getLogger(__name__)


class PreviewWidget(QWidget):
    """Widget for displaying video preview and generation progress"""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("background-color: #2b2b2b; border-radius: 8px;")
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.preview_label)
        
        # Placeholder text
        self.preview_label.setText("Preview Area")
        
    def update_preview(self, image_data: bytes, format_str: str = "jpeg"):
        """
        Update preview with image data
        
        Args:
            image_data: Binary image data
            format_str: Image format ("jpeg" or "png")
        """
        try:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data, format_str.upper())
            
            if not pixmap.isNull():
                # Scale to fit while maintaining aspect ratio
                scaled = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
                self.preview_label.setText("")  # Clear text
            else:
                logger.warning("Failed to load preview image")
                
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            
    def clear(self):
        """Clear preview"""
        self.preview_label.clear()
        self.preview_label.setText("Preview Area")
        
    def resizeEvent(self, event):
        """Handle resize events to scale image"""
        super().resizeEvent(event)
        # If we have a pixmap, re-scale it? 
        # For now, the next update will handle it, or we could store the current pixmap.
        # Simple implementation for now.
