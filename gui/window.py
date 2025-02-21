import requests
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QDialog,
                            QScrollArea, QLabel, QPushButton, QHBoxLayout,
                            QTextEdit, QSplitter, QFileDialog)
from PyQt5.QtCore import Qt, QProcess
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
        try:
            # Create profile directory name
            profile_name = f"PROFILE_{minecraft_version}-Fabric-{loader_version}"
            profile_path = os.path.join('servers', profile_name)
            
            if not os.path.exists(profile_path):
                os.makedirs(profile_path)
            
            # Download server jar
            installer_url = f"https://meta.fabricmc.net/v2/versions/loader/{minecraft_version}/{loader_version}/{installer_version}/server/jar"
            jar_path = os.path.join(profile_path, "server.jar")
            
            # Show download status
            status_label = QLabel("Downloading server jar...")
            status_label.setStyleSheet("color: white;")
            self.version_layout.addWidget(status_label)
            
            response = requests.get(installer_url, stream=True)
            response.raise_for_status()
            
            with open(jar_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Create server files
            with open(os.path.join(profile_path, 'eula.txt'), 'w') as f:
                f.write('eula=true\n')
                
            # Create server.properties with basic settings
            with open(os.path.join(profile_path, 'server.properties'), 'w') as f:
                f.write('server-port=25565\n')
                f.write('difficulty=normal\n')
                f.write('max-players=20\n')
                f.write('view-distance=10\n')
                
            status_label.setText(f"Server created successfully in {profile_path}")
            
            # Refresh main window server list
            if isinstance(self.parent(), ServerTypeDialog):
                main_window = self.parent().parent()
                if isinstance(main_window, MainWindow):
                    main_window.refresh_server_list()
                    
            self.accept()
            
        except Exception as e:
            error_label = QLabel(f"Error creating server: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

class PaperVersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Paper Version")
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
        
        self.fetch_paper_versions()
    
    def fetch_paper_versions(self):
        try:
            response = requests.get("https://api.papermc.io/v2/projects/paper")
            versions = response.json()["versions"]
            
            for version in versions:
                btn = QPushButton(version)
                btn.setStyleSheet(self.button_style)
                btn.clicked.connect(lambda checked, v=version: self.show_builds(v))
                self.version_layout.addWidget(btn)
        except Exception as e:
            error_label = QLabel(f"Error fetching versions: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

    def show_builds(self, version):
        try:
            response = requests.get(f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds")
            builds = response.json()["builds"]
            
            for i in reversed(range(self.version_layout.count())): 
                self.version_layout.itemAt(i).widget().deleteLater()
            
            back_btn = QPushButton("← Back to Versions")
            back_btn.setStyleSheet(self.button_style)
            back_btn.clicked.connect(self.fetch_paper_versions)
            self.version_layout.addWidget(back_btn)
            
            latest_build = builds[-1]  # Get latest build
            btn = QPushButton(f"Build {latest_build['build']}")
            btn.setStyleSheet(self.button_style)
            btn.clicked.connect(lambda checked, v=version, b=latest_build: 
                              self.create_server(v, b))
            self.version_layout.addWidget(btn)
        except Exception as e:
            error_label = QLabel(f"Error fetching builds: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

    def create_server(self, version, build):
        try:
            profile_name = f"PROFILE_{version}-Paper-{build['build']}"
            profile_path = os.path.join('servers', profile_name)
            
            if not os.path.exists(profile_path):
                os.makedirs(profile_path)
            
            jar_name = build["downloads"]["application"]["name"]
            download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build['build']}/downloads/{jar_name}"
            jar_path = os.path.join(profile_path, "server.jar")
            
            status_label = QLabel("Downloading server jar...")
            status_label.setStyleSheet("color: white;")
            self.version_layout.addWidget(status_label)
            
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(jar_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            with open(os.path.join(profile_path, 'eula.txt'), 'w') as f:
                f.write('eula=true\n')
                
            with open(os.path.join(profile_path, 'server.properties'), 'w') as f:
                f.write('server-port=25565\n')
                f.write('difficulty=normal\n')
                f.write('max-players=20\n')
                f.write('view-distance=10\n')
                
            status_label.setText(f"Server created successfully in {profile_path}")
            
            if isinstance(self.parent(), ServerTypeDialog):
                main_window = self.parent().parent()
                if isinstance(main_window, MainWindow):
                    main_window.refresh_server_list()
                    
            self.accept()
            
        except Exception as e:
            error_label = QLabel(f"Error creating server: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

class VanillaVersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Vanilla Version")
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
        
        self.fetch_vanilla_versions()
    
    def fetch_vanilla_versions(self):
        try:
            response = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
            versions = response.json()["versions"]
            
            for version in versions:
                if version["type"] == "release":  # Only show release versions
                    btn = QPushButton(version["id"])
                    btn.setStyleSheet(self.button_style)
                    btn.clicked.connect(lambda checked, v=version: self.create_server(v))
                    self.version_layout.addWidget(btn)
        except Exception as e:
            error_label = QLabel(f"Error fetching versions: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

    def create_server(self, version):
        try:
            profile_name = f"PROFILE_{version['id']}-Vanilla"
            profile_path = os.path.join('servers', profile_name)
            
            if not os.path.exists(profile_path):
                os.makedirs(profile_path)
            
            # Get server jar download URL
            version_meta = requests.get(version["url"]).json()
            download_url = version_meta["downloads"]["server"]["url"]
            jar_path = os.path.join(profile_path, "server.jar")
            
            status_label = QLabel("Downloading server jar...")
            status_label.setStyleSheet("color: white;")
            self.version_layout.addWidget(status_label)
            
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(jar_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            with open(os.path.join(profile_path, 'eula.txt'), 'w') as f:
                f.write('eula=true\n')
                
            with open(os.path.join(profile_path, 'server.properties'), 'w') as f:
                f.write('server-port=25565\n')
                f.write('difficulty=normal\n')
                f.write('max-players=20\n')
                f.write('view-distance=10\n')
                
            status_label.setText(f"Server created successfully in {profile_path}")
            
            if isinstance(self.parent(), ServerTypeDialog):
                main_window = self.parent().parent()
                if isinstance(main_window, MainWindow):
                    main_window.refresh_server_list()
                    
            self.accept()
            
        except Exception as e:
            error_label = QLabel(f"Error creating server: {str(e)}")
            error_label.setStyleSheet("color: red;")
            self.version_layout.addWidget(error_label)

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
        
        # Server type buttons
        fabric_btn = QPushButton("Fabric")
        fabric_btn.setStyleSheet(button_style)
        fabric_btn.clicked.connect(self.show_fabric_dialog)
        layout.addWidget(fabric_btn)
        
        paper_btn = QPushButton("Paper")
        paper_btn.setStyleSheet(button_style)
        paper_btn.clicked.connect(self.show_paper_dialog)
        layout.addWidget(paper_btn)
        
        vanilla_btn = QPushButton("Vanilla")
        vanilla_btn.setStyleSheet(button_style)
        vanilla_btn.clicked.connect(self.show_vanilla_dialog)
        layout.addWidget(vanilla_btn)
        
        self.setLayout(layout)

    def show_fabric_dialog(self):
        dialog = FabricVersionDialog(self)
        dialog.exec_()

    def show_paper_dialog(self):
        dialog = PaperVersionDialog(self)
        dialog.exec_()

    def show_vanilla_dialog(self):
        dialog = VanillaVersionDialog(self)
        dialog.exec_()

class ServerControlPanel(QDialog):
    def __init__(self, server_path, parent=None):
        super().__init__(parent)
        self.server_path = server_path
        self.process = QProcess()
        
        self.setWindowTitle(f"Server Control - {os.path.basename(server_path)}")
        self.setFixedSize(800, 600)
        self.setStyleSheet("background-color: #2b2b2b;")

        layout = QVBoxLayout()
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.power_btn = QPushButton("⚡ Start")
        self.power_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.power_btn.clicked.connect(self.toggle_server)
        
        self.config_btn = QPushButton("⚙ Config")
        self.config_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b3b3b;
                color: white;
                border: none;
                padding: 10px;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #4b4b4b; }
        """)
        self.config_btn.clicked.connect(self.open_config)
        
        button_layout.addWidget(self.power_btn)
        button_layout.addWidget(self.config_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Server console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: none;
                font-family: monospace;
            }
        """)
        layout.addWidget(self.console)
        
        self.setLayout(layout)
        
        # Setup process
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        self.process.finished.connect(self.handle_finished)
        
        self.server_running = False
    
    def find_java_path(self):
        """Find latest installed Java version path"""
        try:
            # Check common Java install locations
            java_paths = [
                "/usr/lib/jvm",
                "/usr/java",
                "/opt/java"
            ]
            
            latest_version = None
            java_path = None
            
            for base_path in java_paths:
                if not os.path.exists(base_path):
                    continue
                    
                for item in os.listdir(base_path):
                    full_path = os.path.join(base_path, item)
                    if not os.path.isdir(full_path):
                        continue
                        
                    # Check if directory contains java binary
                    if os.path.exists(os.path.join(full_path, "bin/java")):
                        version_str = item.replace("java-", "").replace("openjdk-", "")
                        try:
                            version = tuple(map(int, version_str.split(".")[:2]))
                            if not latest_version or version > latest_version:
                                latest_version = version
                                java_path = os.path.join(full_path, "bin/java")
                        except ValueError:
                            continue
            
            return java_path if java_path else "java"
            
        except Exception as e:
            self.console.append(f"Error finding Java: {str(e)}")
            return "java"

    def toggle_server(self):
        if not self.server_running:
            # Find Java path
            java_path = self.find_java_path()
            
            self.power_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 10px;
                    min-width: 100px;
                }
                QPushButton:hover { background-color: #d32f2f; }
            """)
            self.power_btn.setText("⏹ Stop")
            
            java_cmd = ["-Xmx2G", "-jar", "server.jar", "nogui"]
            self.process.setWorkingDirectory(self.server_path)
            self.process.start(java_path, java_cmd)
            self.server_running = True
        else:
            # Stop server
            self.process.write(b"stop\n")
    
    def handle_output(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.console.append(data)
    
    def handle_error(self):
        data = self.process.readAllStandardError().data().decode()
        self.console.append(f"<span style='color: #ff5555'>{data}</span>")
    
    def handle_finished(self):
        self.server_running = False
        self.power_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.power_btn.setText("⚡ Start")
        self.console.append("Server stopped")
    
    def open_config(self):
        config_path = os.path.join(self.server_path, "server.properties")
        if os.path.exists(config_path):
            try:
                # For Linux systems
                os.system(f'xdg-open "{config_path}"')
            except Exception as e:
                self.console.append(f"Error opening config: {str(e)}")

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
                # Connect button to show control panel
                server_path = os.path.join('servers', file)
                btn.clicked.connect(lambda checked, path=server_path: 
                                  self.show_server_control(path))
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

    def refresh_server_list(self):
        # Clear existing widgets
        for i in reversed(range(self.server_layout.count())): 
            widget = self.server_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        # Reload server profiles
        self.load_server_profiles()
    
    def show_server_control(self, server_path):
        dialog = ServerControlPanel(server_path, self)
        dialog.show()