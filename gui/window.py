from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QDialog,
                            QScrollArea, QLabel, QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt
import os

class ServerTypeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Server Type")
        self.setFixedSize(400, 200)
        self.setStyleSheet("background-color: #2b2b2b;")

        layout = QVBoxLayout()
        
        button_style = """
            QPushButton {
                background-color: #3b3b3b;
                color: white;
                border: none;
                padding: 15px;
                min-width: 150px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #4b4b4b;
            }
        """
        
        for server_type in ["Fabric", "Paper", "Vanilla"]:
            btn = QPushButton(server_type)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)
            
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Manager")
        self.setGeometry(100, 100, 800, 600)
        
        # Set background color
        self.setStyleSheet("background-color: #2b2b2b;")
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create scroll area for server list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        # Container for server list
        container = QWidget()
        self.server_layout = QVBoxLayout(container)
        self.server_layout.setAlignment(Qt.AlignCenter)
        
        # Load server profiles
        self.load_server_profiles()
        
        scroll.setWidget(container)
        self.layout.addWidget(scroll)

    def load_server_profiles(self):
        if not os.path.exists('servers'):
            os.makedirs('servers')
            
        for file in os.listdir('servers'):
            if file.startswith('PROFILE_'):
                server_name = file[8:]  # Remove 'PROFILE_' prefix
                btn = QPushButton(server_name)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3b3b3b;
                        color: white;
                        border: none;
                        padding: 10px;
                        min-width: 200px;
                        margin: 5px;
                    }
                    QPushButton:hover {
                        background-color: #4b4b4b;
                    }
                """)
                self.server_layout.addWidget(btn)
        
        if not os.listdir('servers'):
            label = QLabel("No server profiles found")
            label.setStyleSheet("color: white;")
            label.setAlignment(Qt.AlignCenter)
            self.server_layout.addWidget(label)
            
        # Add New Server button
        new_server_btn = QPushButton("+ New Server")
        new_server_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                min-width: 200px;
                margin: 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        new_server_btn.clicked.connect(self.show_server_type_dialog)
        self.server_layout.addWidget(new_server_btn)

    def show_server_type_dialog(self):
        dialog = ServerTypeDialog(self)
        dialog.exec_()