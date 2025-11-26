"""
Visual Preset Library Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QFrame, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QImage
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class PresetCard(QFrame):
    """Card widget for a single preset"""
    
    clicked = pyqtSignal(dict)  # Emits preset data
    
    def __init__(self, preset_data: dict, parent=None):
        super().__init__(parent)
        self.preset_data = preset_data
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Thumbnail (placeholder for now)
        self.image_label = QLabel()
        self.image_label.setMinimumSize(160, 90)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #333; border-radius: 4px;")
        self.image_label.setText(self.preset_data.get('style', 'Style'))
        layout.addWidget(self.image_label)
        
        # Title
        title = QLabel(self.preset_data.get('name', 'Untitled'))
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # Description (truncated prompt)
        prompt = self.preset_data.get('prompt', '')
        if len(prompt) > 50:
            prompt = prompt[:47] + "..."
        desc = QLabel(prompt)
        desc.setStyleSheet("color: #888; font-size: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
    def mousePressEvent(self, event):
        """Handle click event"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.preset_data)
            
    def enterEvent(self, event):
        """Hover effect"""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setStyleSheet("background-color: #2a2a2a;")
        
    def leaveEvent(self, event):
        """Reset hover effect"""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("")


class PresetLibraryWidget(QWidget):
    """Widget for browsing and selecting visual presets"""
    
    preset_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._load_presets()
        
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Header
        header = QLabel("Preset Library")
        header.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Scroll area for grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_widget.setLayout(self.grid_layout)
        
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)
        
    def _load_presets(self):
        """Load presets from file"""
        try:
            presets_file = Path(__file__).parent.parent.parent / "resources" / "presets" / "default_presets.json"
            if presets_file.exists():
                with open(presets_file, 'r') as f:
                    data = json.load(f)
                    presets = data.get('presets', [])
                    
                    row = 0
                    col = 0
                    max_cols = 2
                    
                    for preset in presets:
                        card = PresetCard(preset)
                        card.clicked.connect(self.preset_selected.emit)
                        self.grid_layout.addWidget(card, row, col)
                        
                        col += 1
                        if col >= max_cols:
                            col = 0
                            row += 1
                            
                    # Add spacer to push items up
                    self.grid_layout.setRowStretch(row + 1, 1)
                    
        except Exception as e:
            logger.error(f"Error loading presets: {e}")
