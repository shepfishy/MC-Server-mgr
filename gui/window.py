import requests
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QDialog,
                            QScrollArea, QLabel, QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt
import os

class FabricVersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Fabric Version")
        self.setFixedSize(400, 400)
        self.setStyleSheet("background-color: #2b2b2b;")
        
        self.layout = QVBoxLayout()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.container = QWidget()
        self.version_layout = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)
        
        self.button_style = """
            QPushButton {
                background-color: #3b3b3b;
                color: white;
                border: none;
                padding: 10px;
                min-width: 200px;
                margin: 5px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #4b4b4b;
            }
        """
        
        self.fetch_minecraft_versions()
    
    def fetch_minecraft_versions(self):
        try:
            response = requests.get("https://meta.fabricmc.net/v2/versions/game")
            versions = response.json()
            
            for version in versions:
                if version.get("stable"):  # Only show stable versions
                    btn = QPushButton(version["version"])
                    btn.setStyleSheet(self.button_style)
                    btn.clicked.connect(lambda checked, v=version["version"]: 
                                      self.show_loader_versions(v))
                    self.version_layout.addWidget(btn)
        except Exception as e:
            error_label = QLabel(f"Error fetching versions: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

    def show_loader_versions(self, minecraft_version):
        try:
            response = requests.get(f"https://meta.fabricmc.net/v2/versions/loader/{minecraft_version}")
            versions = response.json()
            
            # Clear previous widgets
            for i in reversed(range(self.version_layout.count())): 
                self.version_layout.itemAt(i).widget().deleteLater()
            
            # Add back button
            back_btn = QPushButton("← Back to Minecraft Versions")
            back_btn.setStyleSheet(self.button_style)
            back_btn.clicked.connect(self.fetch_minecraft_versions)
            self.version_layout.addWidget(back_btn)
            
            for version in versions:
                loader_version = version["loader"]["version"]
                btn = QPushButton(f"Loader {loader_version}")
                btn.setStyleSheet(self.button_style)
                btn.clicked.connect(lambda checked, mv=minecraft_version, lv=loader_version: 
                                  self.show_installer_versions(mv, lv))
                self.version_layout.addWidget(btn)
        except Exception as e:
            error_label = QLabel(f"Error fetching loader versions: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

    def show_installer_versions(self, minecraft_version, loader_version):
        try:
            response = requests.get("https://meta.fabricmc.net/v2/versions/installer")
            versions = response.json()
            
            # Clear previous widgets
            for i in reversed(range(self.version_layout.count())): 
                self.version_layout.itemAt(i).widget().deleteLater()
            
            # Add back button
            back_btn = QPushButton("← Back to Loader Versions")
            back_btn.setStyleSheet(self.button_style)
            back_btn.clicked.connect(lambda: self.show_loader_versions(minecraft_version))
            self.version_layout.addWidget(back_btn)
            
            for version in versions:
                if version.get("stable"):  # Only show stable versions
                    btn = QPushButton(f"Installer {version['version']}")
                    btn.setStyleSheet(self.button_style)
                    btn.clicked.connect(lambda checked, mv=minecraft_version, 
                                      lv=loader_version, iv=version["version"]: 
                                      self.create_server(mv, lv, iv))
                    self.version_layout.addWidget(btn)
        except Exception as e:
            error_label = QLabel(f"Error fetching installer versions: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

    def create_server(self, minecraft_version, loader_version, installer_version):
        # TODO: Implement server creation
        print(f"Creating server with:\nMinecraft: {minecraft_version}\n"
              f"Loader: {loader_version}\nInstaller: {installer_version}")
        self.accept()

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
        
        # Modify Fabric button to open FabricVersionDialog
        fabric_btn = QPushButton("Fabric")
        fabric_btn.setStyleSheet(button_style)  # Use existing style
        fabric_btn.clicked.connect(self.show_fabric_dialog)
        layout.addWidget(fabric_btn)
        
        for server_type in ["Paper", "Vanilla"]:
            btn = QPushButton(server_type)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)
            
        self.setLayout(layout)

    def show_fabric_dialog(self):
        dialog = FabricVersionDialog(self)
        dialog.exec_()

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