import requests
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QDialog,
                            QScrollArea, QLabel, QPushButton, QHBoxLayout,
                            QTextEdit, QSplitter, QFileDialog, QSlider, QLineEdit, QMessageBox)
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QPalette, QBrush, QPixmap
import os
import psutil
# Add this import line for WebUIManager
from gui.webui import WebUIManager

# Make sure this is outside all classes
web_ui_manager = None

def initialize_web_ui():
    global web_ui_manager
    if (web_ui_manager is None):
        print("Initializing WebUI Manager")
        web_ui_manager = WebUIManager()
        
        # Connect signals to slots using Qt.QueuedConnection to ensure thread safety
        web_ui_manager.process_handler.start_server_signal.connect(
            web_ui_manager.process_handler.start_server,
            type=Qt.QueuedConnection
        )
        web_ui_manager.process_handler.stop_server_signal.connect(
            web_ui_manager.process_handler.stop_server,
            type=Qt.QueuedConnection
        )
        web_ui_manager.process_handler.send_command_signal.connect(
            web_ui_manager.process_handler.send_command,
            type=Qt.QueuedConnection
        )
        
        # Start the web UI server
        web_ui_manager.start()
        print("WebUI Manager initialized")
    return web_ui_manager

class Styles:
    # Background with SVG support
    @staticmethod
    def set_background_image(widget, image_path):
        if (image_path.lower().endswith('.svg')):
            palette = QPalette()
            pixmap = QPixmap(image_path)
            brush = QBrush(pixmap)
            palette.setBrush(QPalette.Window, brush)
            widget.setAutoFillBackground(True)
            widget.setPalette(palette)
        else:
            widget.setStyleSheet(f"background-image: url({image_path}); background-repeat: no-repeat; background-position: center; background-size: cover;")
    
    BACKGROUND = """
        background-color: #212121;
        color: #f0f0f0;
    """
    
    BUTTON = """
        QPushButton {
            background-color: #2d2d2d;
            color: #f0f0f0;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 12px;
            min-width: 200px;
            margin: 5px;
            text-align: left;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
            border-color: #666666;
        }
        QPushButton:pressed {
            background-color: #1e1e1e;
        }
    """
    
    ACTION_BUTTON = """
        QPushButton {
            background-color: #388E3C;
            color: white;
            border: 1px solid #2E7D32;
            border-radius: 4px;
            padding: 12px;
            min-width: 100px;
            margin: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #43A047;
        }
        QPushButton:pressed {
            background-color: #2E7D32;
        }
    """
    
    STOP_BUTTON = """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: 1px solid #d32f2f;
            padding: 10px;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #d32f2f;
        }
    """
    
    CONFIG_BUTTON = """
        QPushButton {
            background-color: #3b3b3b;
            color: white;
            border: 1px solid #555555;
            padding: 10px;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #4b4b4b;
        }
    """
    
    CONSOLE = """
        QTextEdit {
            background-color: #1e1e1e;
            color: #ffffff;
            border: none;
            font-family: monospace;
        }
    """
    
    SCROLL_AREA = "QScrollArea { border: none; }"
    
    LABEL = "color: white;"
    ERROR_LABEL = "color: red;"
    
    SVG_BUTTON = """
        QPushButton {
            background-color: transparent;
            border: none;
            padding: 10px;
            min-width: 100px;
            margin: 5px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
    """

class FabricVersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Fabric Version")
        self.setFixedSize(400, 400)
        self.setStyleSheet(Styles.BACKGROUND)
        
        self.layout = QVBoxLayout()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(Styles.SCROLL_AREA)
        
        self.container = QWidget()
        self.version_layout = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)
        
        self.button_style = Styles.BUTTON
        
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
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
            status_label.setStyleSheet(Styles.LABEL)
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
            self.version_layout.addWidget(error_label)

class PaperVersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Paper Version")
        self.setFixedSize(400, 400)
        self.setStyleSheet(Styles.BACKGROUND)
        
        self.layout = QVBoxLayout()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(Styles.SCROLL_AREA)
        
        self.container = QWidget()
        self.version_layout = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)
        
        self.button_style = Styles.BUTTON
        
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
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
            status_label.setStyleSheet(Styles.LABEL)
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
            self.version_layout.addWidget(error_label)

class VanillaVersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Vanilla Version")
        self.setFixedSize(400, 400)
        self.setStyleSheet(Styles.BACKGROUND)
        
        self.layout = QVBoxLayout()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(Styles.SCROLL_AREA)
        
        self.container = QWidget()
        self.version_layout = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)
        
        self.button_style = Styles.BUTTON
        
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
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
            status_label.setStyleSheet(Styles.LABEL)
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
            error_label.setStyleSheet(Styles.ERROR_LABEL)
            self.version_layout.addWidget(error_label)

class ServerTypeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Server Type")
        self.setFixedSize(400, 200)
        self.setStyleSheet(Styles.BACKGROUND)

        layout = QVBoxLayout()
        
        button_style = Styles.BUTTON
        
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
        self.parent_window = parent
        self.server_running = False
        
        # Setup process signals first
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        self.process.finished.connect(self.handle_finished)
        
        # Register with web UI manager if parent window has one
        if hasattr(parent, 'webui_manager'):
            print(f"Registering server panel for {server_path} with WebUIManager")
            parent.webui_manager.add_server_profile(server_path, self)
        
        self.setWindowTitle(f"Server Control - {os.path.basename(server_path)}")
        self.setFixedSize(800, 600)
        self.setStyleSheet(Styles.BACKGROUND)

        layout = QVBoxLayout()
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.power_btn = QPushButton("⚡ Start")
        self.power_btn.setStyleSheet(Styles.ACTION_BUTTON)
        self.power_btn.clicked.connect(self.toggle_server)
        
        self.config_btn = QPushButton("⚙ Config")
        self.config_btn.setStyleSheet(Styles.CONFIG_BUTTON)
        self.config_btn.clicked.connect(self.open_config)
        
        self.modrinth_btn = QPushButton("🧩 Mods")
        self.modrinth_btn.setStyleSheet(Styles.CONFIG_BUTTON)
        self.modrinth_btn.clicked.connect(self.show_mod_dialog)
        
        button_layout.addWidget(self.power_btn)
        button_layout.addWidget(self.config_btn)
        button_layout.addWidget(self.modrinth_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Add memory slider
        memory_layout = QHBoxLayout()
        memory_label = QLabel("Memory (GB):")
        memory_label.setStyleSheet(Styles.LABEL)
        self.memory_slider = QSlider(Qt.Horizontal)
        self.memory_slider.setMinimum(1)
        self.memory_slider.setMaximum(32)
        self.memory_slider.setValue(2)  # Default 2GB
        self.memory_slider.setTickPosition(QSlider.TicksBelow)
        self.memory_slider.setTickInterval(1)
        self.memory_value = QLabel("2")
        self.memory_value.setStyleSheet(Styles.LABEL)
        self.memory_slider.valueChanged.connect(self.update_memory_label)
        
        memory_layout.addWidget(memory_label)
        memory_layout.addWidget(self.memory_slider)
        memory_layout.addWidget(self.memory_value)
        
        # Add memory layout above console
        layout.addLayout(memory_layout)
        
        # Server console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(Styles.CONSOLE)
        layout.addWidget(self.console)
        
        self.setLayout(layout)
    
    def handle_output(self):
        try:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            
            # Update desktop UI console
            if hasattr(self, 'console'):
                self.console.append(data)
            
            # Send to web UI console if we have a parent with web UI
            if hasattr(self.parent_window, 'webui_manager'):
                webui = self.parent_window.webui_manager
                if self.server_path in webui.console_buffers:
                    for line in data.splitlines():
                        if line.strip():  # Only add non-empty lines
                            webui.console_buffers[self.server_path].add_line(line)
                            # Also print for debugging
                            print(f"Server output: {line}")
        except Exception as e:
            print(f"Error handling process output: {str(e)}")

    def handle_error(self):
        try:
            data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
            
            # Update desktop UI console
            if hasattr(self, 'console'):
                self.console.append(f"<span style='color: #ff5555'>{data}</span>")
            
            # Send to web UI console if we have a parent with web UI
            if hasattr(self.parent_window, 'webui_manager'):
                webui = self.parent_window.webui_manager
                if self.server_path in webui.console_buffers:
                    for line in data.splitlines():
                        if line.strip():  # Only add non-empty lines
                            webui.console_buffers[self.server_path].add_line(f"[ERROR] {line}")
                            # Also print for debugging
                            print(f"Server error: {line}")
        except Exception as e:
            print(f"Error handling process error output: {str(e)}")

    def handle_finished(self):
        self.server_running = False
        
        # Update desktop UI
        if hasattr(self, 'power_btn'):
            self.power_btn.setStyleSheet(Styles.ACTION_BUTTON)
            self.power_btn.setText("⚡ Start")
        
        # Add message to desktop UI console
        if hasattr(self, 'console'):
            self.console.append("Server stopped")
        
        # Send to web UI console if we have a parent with web UI
        if hasattr(self.parent_window, 'webui_manager'):
            webui = self.parent_window.webui_manager
            if self.server_path in webui.console_buffers:
                webui.console_buffers[self.server_path].add_line("Server stopped")

    def start_from_web(self):
        """Method to allow web UI to start the server"""
        print("Server start requested from web UI")
        if not self.server_running:
            self.toggle_server()
            return True
        return False

    def find_java_path(self):
        """Find latest installed Java version path"""
        try:
            # Check common Java install locations
            java_paths = []
            
            if os.name == 'nt':  # Windows
                java_paths.extend([
                    "C:\\Program Files\\Java",
                    "C:\\Program Files (x86)\\Java",
                    os.path.join(os.getenv('LOCALAPPDATA', ''), "Programs\\Java"),
                    os.path.join(os.getenv('PROGRAMDATA', ''), "Java")
                ])
            else:  # Linux/Unix
                java_paths.extend([
                    "/usr/lib/jvm",
                    "/usr/java",
                    "/opt/java"
                ])
            
            latest_version = None
            java_path = None
            
            for base_path in java_paths:
                if not os.path.exists(base_path):
                    continue
                    
                for item in os.listdir(base_path):
                    full_path = os.path.join(base_path, item)
                    if not os.path.isdir(full_path):
                        continue
                        
                    # Check for java binary based on OS
                    java_bin = "bin\\java.exe" if os.name == 'nt' else "bin/java"
                    if os.path.exists(os.path.join(full_path, java_bin)):
                        version_str = item.replace("java-", "").replace("openjdk-", "").replace("jdk", "")
                        try:
                            version = tuple(map(int, version_str.split(".")[:2]))
                            if not latest_version or version > latest_version:
                                latest_version = version
                                java_path = os.path.join(full_path, java_bin)
                        except ValueError:
                            continue
            
            return java_path if java_path else ("java.exe" if os.name == 'nt' else "java")
            
        except Exception as e:
            self.console.append(f"Error finding Java: {str(e)}")
            return "java.exe" if os.name == 'nt' else "java"

    def update_memory_label(self):
        self.memory_value.setText(str(self.memory_slider.value()))
    
    def toggle_server(self):
        try:
            if not self.server_running:
                # Find Java path
                java_path = self.find_java_path()
                print(f"Starting server with Java path: {java_path}")
                
                # Update UI if we have a power button
                if hasattr(self, 'power_btn'):
                    self.power_btn.setStyleSheet(Styles.STOP_BUTTON)
                    self.power_btn.setText("⏹ Stop")
                
                # Get memory allocation (default to 2GB if slider doesn't exist)
                memory = 2
                if hasattr(self, 'memory_slider'):
                    memory = self.memory_slider.value()
                
                # Ensure process is connected to signal handlers
                # Use try/except instead of the receivers() method
                try:
                    self.process.readyReadStandardOutput.disconnect(self.handle_output)
                    self.process.readyReadStandardOutput.connect(self.handle_output)
                except TypeError:
                    self.process.readyReadStandardOutput.connect(self.handle_output)
                    
                try:
                    self.process.readyReadStandardError.disconnect(self.handle_error)
                    self.process.readyReadStandardError.connect(self.handle_error)
                except TypeError:
                    self.process.readyReadStandardError.connect(self.handle_error)
                    
                try:
                    self.process.finished.disconnect(self.handle_finished)
                    self.process.finished.connect(self.handle_finished)
                except TypeError:
                    self.process.finished.connect(self.handle_finished)
                    
                java_cmd = [f"-Xmx{memory}G", "-jar", "server.jar", "nogui"]
                
                print(f"Setting working directory: {self.server_path}")
                self.process.setWorkingDirectory(self.server_path)
                
                cmd_str = f"{java_path} {' '.join(java_cmd)}"
                print(f"Starting process with command: {cmd_str}")
                
                # Add the command to both desktop UI and web UI console
                if hasattr(self, 'console'):
                    self.console.append(f"Executing: {cmd_str}")
                
                # Send to web UI console if we have a parent with web UI
                if hasattr(self.parent_window, 'webui_manager'):
                    webui = self.parent_window.webui_manager
                    if self.server_path in webui.console_buffers:
                        webui.console_buffers[self.server_path].add_line(f"Executing: {cmd_str}")
                
                # Start the server
                self.process.start(java_path, java_cmd)
                
                self.server_running = True
                print(f"Server marked as running: {self.server_path}")
                
                return True
            else:
                # Stop server
                print(f"Stopping server: {self.server_path}")
                if hasattr(self, 'process') and self.process:
                    # Send stop command to server
                    stop_cmd = "stop\n"
                    self.process.write(stop_cmd.encode('utf-8'))
                    
                    # Update desktop UI console
                    if hasattr(self, 'console'):
                        self.console.append("Stopping server...")
                    
                    # Send to web UI console if we have a parent with web UI
                    if hasattr(self.parent_window, 'webui_manager'):
                        webui = self.parent_window.webui_manager
                        if self.server_path in webui.console_buffers:
                            webui.console_buffers[self.server_path].add_line("Stopping server...")
                    
                    self.server_running = False
                    
                    # Update UI if we have a power button
                    if hasattr(self, 'power_btn'):
                        self.power_btn.setStyleSheet(Styles.ACTION_BUTTON)
                        self.power_btn.setText("⚡ Start")
                        
                    return True
        except Exception as e:
            print(f"Error in toggle_server: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def open_config(self):
        config_path = os.path.join(self.server_path, "server.properties")
        if os.path.exists(config_path):
            try:
                # For Linux systems
                os.system(f'xdg-open "{config_path}"')
            except Exception as e:
                self.console.append(f"Error opening config: {str(e)}")

    def show_mod_dialog(self):
        dialog = ModrinthDialog(self.server_path, self)
        dialog.exec_()

    def __repr__(self):
        return f"ServerControlPanel({self.server_path})"

class ModrinthDialog(QDialog):
    def __init__(self, server_path, parent=None):
        super().__init__(parent)
        self.server_path = server_path
        self.setWindowTitle("Install Mods")
        self.setFixedSize(800, 600)
        self.setStyleSheet(Styles.BACKGROUND)

        layout = QVBoxLayout()
        
        # Search box
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setStyleSheet("background: #333; color: white; padding: 5px;")
        self.search_box.setPlaceholderText("Search mods...")
        search_btn = QPushButton("Search")
        search_btn.setStyleSheet(Styles.ACTION_BUTTON)
        search_btn.clicked.connect(self.search_mods)
        
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Mod list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(Styles.SCROLL_AREA)
        
        self.mod_container = QWidget()
        self.mod_layout = QVBoxLayout(self.mod_container)
        scroll.setWidget(self.mod_container)
        layout.addWidget(scroll)
        
        self.setLayout(layout)

    def search_mods(self):
        query = self.search_box.text()
        try:
            # Clear previous results
            for i in reversed(range(self.mod_layout.count())):
                self.mod_layout.itemAt(i).widget().deleteLater()
                
            # Search Modrinth API
            headers = {
                "User-Agent": "MinecraftServerManager/1.0"
            }
            params = {
                "query": query,
                "limit": 20,
                "project_type": "mod"
            }
            response = requests.get(
                "https://api.modrinth.com/v2/search", 
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("hits"):
                error = QLabel("No mods found")
                error.setStyleSheet(Styles.LABEL)
                self.mod_layout.addWidget(error)
                return

            for mod in data["hits"]:
                mod_widget = QWidget()
                mod_layout = QHBoxLayout(mod_widget)
                
                title = QLabel(f"<b>{mod['title']}</b><br>{mod['description']}")
                title.setStyleSheet(Styles.LABEL)
                title.setWordWrap(True)
                
                install_btn = QPushButton("Install")
                install_btn.setStyleSheet(Styles.ACTION_BUTTON)
                install_btn.clicked.connect(lambda checked, m=mod: self.install_mod(m))
                
                mod_layout.addWidget(title)
                mod_layout.addWidget(install_btn)
                
                self.mod_layout.addWidget(mod_widget)
                
        except Exception as e:
            error = QLabel(f"Error searching mods: {str(e)}")
            error.setStyleSheet(Styles.ERROR_LABEL)
            self.mod_layout.addWidget(error)

    def install_mod(self, mod):
        try:
            # Create version selection dialog
            version_dialog = QDialog(self)
            version_dialog.setWindowTitle("Select Mod Version")
            version_dialog.setFixedSize(400, 400)
            version_dialog.setStyleSheet(Styles.BACKGROUND)
            
            layout = QVBoxLayout()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(Styles.SCROLL_AREA)
            
            container = QWidget()
            version_layout = QVBoxLayout(container)
            scroll.setWidget(container)
            layout.addWidget(scroll)
            version_dialog.setLayout(layout)

            # Get all versions from Modrinth
            version_id = mod["project_id"]
            headers = {"User-Agent": "MinecraftServerManager/1.0"}
            response = requests.get(
                f"https://api.modrinth.com/v2/project/{version_id}/version",
                headers=headers
            )
            versions = response.json()

            # Add version buttons
            for version in versions:
                # Create version info text
                version_info = (
                    f"Version: {version['version_number']}\n"
                    f"Game Versions: {', '.join(version['game_versions'])}\n"
                    f"Loaders: {', '.join(version['loaders'])}"
                )
                
                btn = QPushButton(version_info)
                btn.setStyleSheet(Styles.BUTTON)
                btn.clicked.connect(lambda checked, v=version: self.download_mod(v, mod["title"]))
                version_layout.addWidget(btn)

            version_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get mod versions: {str(e)}")

    def download_mod(self, version, mod_title):
        try:
            # Create mods folder if needed
            mods_path = os.path.join(self.server_path, "mods")
            if not os.path.exists(mods_path):
                os.makedirs(mods_path)

            # Download the mod file
            file_url = version["files"][0]["url"]
            file_name = version["files"][0]["filename"]
            
            response = requests.get(file_url, stream=True)
            response.raise_for_status()
            
            with open(os.path.join(mods_path, file_name), 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            QMessageBox.information(
                self,
                "Success",
                f"Installed {mod_title} {version['version_number']}\n"
                f"Game versions: {', '.join(version['game_versions'])}\n"
                f"Loaders: {', '.join(version['loaders'])}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download mod: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Manager")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize web UI manager
        self.webui_manager = initialize_web_ui()
        
        # Make sure to add all existing server profiles
        if os.path.exists('servers'):
            for file in os.listdir('servers'):
                if file.startswith('PROFILE_'):
                    server_path = os.path.join('servers', file)
                    # Create a minimal control panel object for each server
                    control_panel = self.create_minimal_panel(server_path)
                    self.webui_manager.add_server_profile(server_path, control_panel)
        
        # Set background color
        self.setStyleSheet(Styles.BACKGROUND)
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create scroll area for server list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(Styles.SCROLL_AREA)
        
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
                btn.setStyleSheet(Styles.BUTTON)
                # Connect button to show control panel
                server_path = os.path.join('servers', file)
                btn.clicked.connect(lambda checked, path=server_path: 
                                  self.show_server_control(path))
                self.server_layout.addWidget(btn)
        
        if not os.listdir('servers'):
            label = QLabel("No server profiles found")
            label.setStyleSheet(Styles.LABEL)
            label.setAlignment(Qt.AlignCenter)
            self.server_layout.addWidget(label)
            
        # Add New Server button
        new_server_btn = QPushButton("+ New Server")
        new_server_btn.setStyleSheet(Styles.ACTION_BUTTON)
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
    
    def create_minimal_panel(self, server_path):
        """
        Create a minimal panel object to represent a server
        that hasn't been opened yet in the GUI
        """
        panel = ServerControlPanel(server_path, self)
        return panel