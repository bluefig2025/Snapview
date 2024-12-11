import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QFileDialog,
                                 QHBoxLayout, QMenuBar, QMenu, QStatusBar, QDialog, QFormLayout, QColorDialog, QSpinBox, QCheckBox, QDialogButtonBox)
from PySide6.QtGui import QPixmap, QTransform, QPainter, QIcon, QAction
from PySide6.QtCore import Qt, QPoint

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        # Settings layout
        layout = QFormLayout()

        # Default Zoom Level
        self.zoom_spinbox = QSpinBox()
        self.zoom_spinbox.setRange(1, 500)
        self.zoom_spinbox.setValue(100)  # Default value
        layout.addRow("Default Zoom (%)", self.zoom_spinbox)

        # Background Color
        self.bg_color_button = QPushButton("Choose Color")
        self.bg_color_button.clicked.connect(self.choose_color)
        self.bg_color = "lightgray"  # Default color
        layout.addRow("Background Color", self.bg_color_button)

        # Enable Mouse Dragging
        self.enable_drag_checkbox = QCheckBox()
        self.enable_drag_checkbox.setChecked(True)  # Default enabled
        layout.addRow("Enable Mouse Dragging", self.enable_drag_checkbox)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.bg_color = color.name()

class SnapView(QMainWindow):
    SETTINGS_FILE = "settings.json"

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SnapView v1.0")
        self.setGeometry(100, 100, 800, 600)

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layouts
        self.layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Menu Bar
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        file_menu = QMenu("File", self)
        self.menu_bar.addMenu(file_menu)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_image)
        file_menu.addAction(save_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = QMenu("Settings", self)
        self.menu_bar.addMenu(settings_menu)

        settings_action = QAction("Preferences", self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # Image display
        self.image_label = QLabel("No image loaded.")
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("background-color: lightgray;")
        self.layout.addWidget(self.image_label)

        # Buttons
        self.open_button = QPushButton("Open Image")
        self.open_button.clicked.connect(self.open_image)

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_in_button.setEnabled(False)

        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_out_button.setEnabled(False)

        self.rotate_button = QPushButton("Rotate")
        self.rotate_button.clicked.connect(self.rotate_image)
        self.rotate_button.setEnabled(False)

        self.fullscreen_button = QPushButton("Fullscreen")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)

        # Add buttons to layout above the image
        self.button_layout.addWidget(self.open_button)
        self.button_layout.addWidget(self.zoom_in_button)
        self.button_layout.addWidget(self.zoom_out_button)
        self.button_layout.addWidget(self.rotate_button)
        self.button_layout.addWidget(self.fullscreen_button)

        self.layout.addLayout(self.button_layout)

        # State
        self.pixmap = None
        self.scale_factor = 1.0
        self.rotation_angle = 0
        self.image_offset = QPoint(0, 0)
        self.dragging = False
        self.last_mouse_position = QPoint(0, 0)

        self.default_zoom = 1.0
        self.bg_color = "lightgray"
        self.enable_dragging = True

        # Load settings
        self.load_settings()

        # Enable mouse tracking
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.start_drag
        self.image_label.mouseMoveEvent = self.drag_image
        self.image_label.mouseReleaseEvent = self.end_drag

    def load_settings(self):
        try:
            with open(self.SETTINGS_FILE, "r") as file:
                settings = json.load(file)
                self.default_zoom = settings.get("default_zoom", 1.0)
                self.bg_color = settings.get("bg_color", "lightgray")
                self.enable_dragging = settings.get("enable_dragging", True)
                self.image_label.setStyleSheet(f"background-color: {self.bg_color};")
        except FileNotFoundError:
            self.save_settings()

    def save_settings(self):
        settings = {
            "default_zoom": self.default_zoom,
            "bg_color": self.bg_color,
            "enable_dragging": self.enable_dragging
        }
        with open(self.SETTINGS_FILE, "w") as file:
            json.dump(settings, file)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.zoom_spinbox.setValue(int(self.default_zoom * 100))
        dialog.bg_color = self.bg_color
        dialog.enable_drag_checkbox.setChecked(self.enable_dragging)

        if dialog.exec():
            # Apply settings
            self.default_zoom = dialog.zoom_spinbox.value() / 100.0
            self.bg_color = dialog.bg_color
            self.enable_dragging = dialog.enable_drag_checkbox.isChecked()

            # Save settings
            self.save_settings()

            # Update UI
            self.image_label.setStyleSheet(f"background-color: {self.bg_color};")
            self.scale_factor = self.default_zoom
            self.update_image()

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.pixmap = QPixmap(file_path)
            self.image_label.setPixmap(self.pixmap)
            self.image_label.setText("")

            # Enable buttons
            self.zoom_in_button.setEnabled(True)
            self.zoom_out_button.setEnabled(True)
            self.rotate_button.setEnabled(True)

            # Reset state
            self.scale_factor = self.default_zoom
            self.rotation_angle = 0
            self.image_offset = QPoint(0, 0)
            self.update_image()

            self.status_bar.showMessage(f"Loaded image: {file_path}")

    def save_image(self):
        if self.pixmap:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
            if file_path:
                self.pixmap.save(file_path)
                self.status_bar.showMessage(f"Image saved: {file_path}")

    def zoom_in(self):
        if self.pixmap:
            self.scale_factor += 0.1
            self.update_image()
            self.status_bar.showMessage(f"Zoomed In: {self.scale_factor * 100:.0f}%")

    def zoom_out(self):
        if self.pixmap and self.scale_factor > 0.1:
            self.scale_factor -= 0.1
            self.update_image()
            self.status_bar.showMessage(f"Zoomed Out: {self.scale_factor * 100:.0f}%")

    def rotate_image(self):
        if self.pixmap:
            self.rotation_angle += 90
            self.update_image()
            self.status_bar.showMessage(f"Image Rotated: {self.rotation_angle}°")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.status_bar.showMessage("Exited Fullscreen Mode")
        else:
            self.showFullScreen()
            self.status_bar.showMessage("Entered Fullscreen Mode")

    def start_drag(self, event):
        if self.pixmap and self.enable_dragging and event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_position = event.position().toPoint()

    def drag_image(self, event):
        if self.dragging and self.pixmap:
            delta = event.position().toPoint() - self.last_mouse_position
            self.image_offset += delta
            self.last_mouse_position = event.position().toPoint()
            self.update_image()

    def end_drag(self, event):
        if self.pixmap and event.button() == Qt.LeftButton:
            self.dragging = False

    def update_image(self):
        if self.pixmap:
            transform = QTransform()
            transform.rotate(self.rotation_angle)
            transformed_pixmap = self.pixmap.transformed(transform, mode=Qt.SmoothTransformation)

            scaled_pixmap = transformed_pixmap.scaled(
                self.pixmap.size() * self.scale_factor,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )

            # Create a painter to draw the pixmap with the current offset
            canvas = QPixmap(self.image_label.size())
            canvas.fill(Qt.lightGray)
            painter = QPainter(canvas)
            painter.drawPixmap(self.image_offset, scaled_pixmap)
            painter.end()

            self.image_label.setPixmap(canvas)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = SnapView()
    window.show()

    sys.exit(app.exec())
