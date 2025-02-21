from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Manager")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Add widgets
        self.label = QLabel("Minecraft Server Manager")
        self.button = QPushButton("Test Button")
        
        # Add widgets to layout
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.button)
        
        # Important: Show the window
        self.show()