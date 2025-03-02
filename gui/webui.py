from flask import Flask, render_template, jsonify, send_from_directory, request, redirect
import os
import psutil
import threading
import time
from PyQt5.QtCore import QProcess, pyqtSignal, QObject, pyqtSlot, Qt
import subprocess
import json

class ConsoleBuffer:
    def __init__(self, max_lines=100):
        self.lines = []
        self.max_lines = max_lines
        self.lock = threading.Lock()
    
    def add_line(self, line):
        with self.lock:
            self.lines.append(line)
            if len(self.lines) > self.max_lines:
                self.lines.pop(0)
    
    def get_lines(self):
        with self.lock:
            return self.lines.copy()

class ServerProcessHandler(QObject):
    """Helper class to handle server process commands from web UI thread"""
    start_server_signal = pyqtSignal(str)  # Signal to start server - sends server path
    stop_server_signal = pyqtSignal(str)   # Signal to stop server - sends server path
    send_command_signal = pyqtSignal(str, str)  # Signal to send command - (server path, command)
    
    def __init__(self, web_manager):
        super().__init__()
        self.web_manager = web_manager
    
    @pyqtSlot(str)
    def start_server(self, server_path):
        """Start server in main thread"""
        try:
            print(f"Starting server via WebUI for path: {server_path}")
            if server_path in self.web_manager.profiles:
                control_panel = self.web_manager.profiles[server_path]
                if hasattr(control_panel, 'toggle_server'):
                    # Make sure server is not marked as running
                    control_panel.server_running = False
                    # Start the server
                    success = control_panel.toggle_server()
                    self.web_manager.console_buffers[server_path].add_line("Server starting...")
                    print(f"Server start result: {success}")
                    return True
                else:
                    print(f"Control panel missing toggle_server method for {server_path}")
            else:
                print(f"Server path {server_path} not found in profiles")
            return False
        except Exception as e:
            print(f"Error in start_server: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    @pyqtSlot(str)
    def stop_server(self, server_path):
        """Stop server in main thread"""
        try:
            print(f"Stopping server via WebUI for path: {server_path}")
            if server_path in self.web_manager.profiles:
                control_panel = self.web_manager.profiles[server_path]
                if hasattr(control_panel, 'process') and control_panel.process:
                    if control_panel.process.state() == QProcess.Running:
                        print(f"Sending stop command to process")
                        control_panel.process.write(b"stop\n")
                        self.web_manager.console_buffers[server_path].add_line("Server stopping...")
                        
                        # Make sure to update the server_running state in the control panel
                        control_panel.server_running = False
                        
                        return True
                    else:
                        print(f"Process not running for {server_path}")
                else:
                    print(f"Process not available for {server_path}")
            else:
                print(f"Server path {server_path} not found in profiles")
            return False
        except Exception as e:
            print(f"Error in stop_server: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    @pyqtSlot(str, str)
    def send_command(self, server_path, command):
        """Send command to server in main thread"""
        try:
            print(f"Sending command via WebUI for path: {server_path}, command: {command}")
            if server_path in self.web_manager.profiles:
                control_panel = self.web_manager.profiles[server_path]
                if hasattr(control_panel, 'process') and control_panel.process:
                    if control_panel.process.state() == QProcess.Running:
                        print(f"Sending command to process")
                        control_panel.process.write(f"{command}\n".encode('utf-8'))
                        self.web_manager.console_buffers[server_path].add_line(f"> {command}")
                        return True
                    else:
                        print(f"Process not running for {server_path}")
                else:
                    print(f"Process not available for {server_path}")
            else:
                print(f"Server path {server_path} not found in profiles")
            return False
        except Exception as e:
            print(f"Error in send_command: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

class WebUIManager:
    """Central manager for the web UI interface"""
    def __init__(self):
        self.app = None
        self.thread = None
        self.running = False
        self.profiles = {}  # Dictionary of server paths to ServerControlPanel objects
        self.console_buffers = {}  # Dictionary of server paths to console buffers
        
        # Create process handler to run operations in main thread
        self.process_handler = ServerProcessHandler(self)
        
    def add_server_profile(self, server_path, control_panel):
        """Register a server profile with the web UI"""
        print(f"Adding server profile for {server_path}")
        self.profiles[server_path] = control_panel
        self.console_buffers[server_path] = ConsoleBuffer(500)
        
        # Connect signals for console output
        if hasattr(control_panel, 'process') and control_panel.process:
            print(f"Connecting process signals for {server_path}")
            
            # Disconnect any existing connections to avoid duplicates
            try:
                control_panel.process.readyReadStandardOutput.disconnect()
                control_panel.process.readyReadStandardOutput.connect(
                    lambda: self.capture_stdout(server_path)
                )
            except:
                # Connect if not already connected
                control_panel.process.readyReadStandardOutput.connect(
                    lambda: self.capture_stdout(server_path)
                )
                
            try:
                control_panel.process.readyReadStandardError.disconnect()
                control_panel.process.readyReadStandardError.connect(
                    lambda: self.capture_stderr(server_path)
                )
            except:
                # Connect if not already connected
                control_panel.process.readyReadStandardError.connect(
                    lambda: self.capture_stderr(server_path)
                )
        else:
            print(f"Process not available for {server_path}, will connect when server starts")
    
    def capture_stdout(self, server_path):
        """Capture stdout from server process"""
        if server_path in self.profiles:
            control_panel = self.profiles[server_path]
            if hasattr(control_panel, 'process') and control_panel.process:
                try:
                    data = control_panel.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
                    for line in data.splitlines():
                        if line.strip():
                            self.console_buffers[server_path].add_line(line)
                            print(f"Captured stdout for {server_path}: {line}")
                except Exception as e:
                    print(f"Error capturing stdout: {str(e)}")

    def capture_stderr(self, server_path):
        """Capture stderr from server process"""
        if server_path in self.profiles:
            control_panel = self.profiles[server_path]
            if hasattr(control_panel, 'process') and control_panel.process:
                try:
                    data = control_panel.process.readAllStandardError().data().decode('utf-8', errors='replace')
                    for line in data.splitlines():
                        if line.strip():
                            self.console_buffers[server_path].add_line(f"[ERROR] {line}")
                            print(f"Captured stderr for {server_path}: {line}")
                except Exception as e:
                    print(f"Error capturing stderr: {str(e)}")

    def setup_app(self):
        # Create Flask app
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            """Show list of server profiles"""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Minecraft Server Manager</title>
                <style>
                    /* Modern UI Theme with Minecraft Inspiration */
                    :root {
                        --primary: #4CAF50;
                        --primary-dark: #388E3C;
                        --primary-light: #81C784;
                        --secondary: #2196F3;
                        --secondary-dark: #1976D2;
                        --danger: #F44336;
                        --danger-dark: #D32F2F;
                        --warning: #FF9800;
                        --success: #4CAF50;
                        --dark: #212121;
                        --dark-lighter: #2d2d2d;
                        --dark-medium: #383838;
                        --dark-border: #444444;
                        --text: #f0f0f0;
                        --text-muted: #aaaaaa;
                        --shadow: rgba(0,0,0,0.2);
                    }

                    body {
                        background: var(--dark);
                        color: var(--text);
                        font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        line-height: 1.6;
                        background-image: linear-gradient(to bottom, #1a1a1a, #212121);
                        min-height: 100vh;
                        position: relative;
                        overflow-x: hidden;
                    }

                    body::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 200px;
                        background-image: linear-gradient(to bottom, rgba(76, 175, 80, 0.05), transparent);
                        z-index: -1;
                    }

                    h1, h2, h3 {
                        font-weight: 600;
                        margin-top: 0;
                        color: var(--primary);
                        letter-spacing: 0.5px;
                    }

                    h1 {
                        font-size: 28px;
                        border-bottom: 2px solid var(--primary-dark);
                        padding-bottom: 10px;
                        margin-bottom: 25px;
                        display: inline-block;
                    }

                    .header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 30px;
                        padding-bottom: 15px;
                        border-bottom: 1px solid var(--dark-border);
                    }

                    .back-button {
                        background-color: var(--dark-medium);
                        color: var(--text);
                        border: none;
                        padding: 10px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        font-weight: 500;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        box-shadow: 0 2px 5px var(--shadow);
                    }

                    .back-button:hover {
                        background-color: var(--dark-border);
                        transform: translateY(-2px);
                    }

                    .back-button::before {
                        content: '←';
                        font-size: 18px;
                        line-height: 1;
                    }

                    .status-card {
                        background: var(--dark-lighter);
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        border: 1px solid var(--dark-border);
                        box-shadow: 0 4px 15px var(--shadow);
                        transition: all 0.3s ease;
                        position: relative;
                        overflow: hidden;
                    }

                    .status-card:hover {
                        transform: translateY(-3px);
                        box-shadow: 0 6px 20px var(--shadow);
                        border-color: var(--primary-dark);
                    }

                    .status-card::after {
                        content: '';
                        position: absolute;
                        top: 0;
                        right: 0;
                        width: 80px;
                        height: 80px;
                        background: linear-gradient(135deg, transparent 70%, rgba(76, 175, 80, 0.1) 100%);
                        border-radius: 0 0 0 80px;
                    }

                    .metric {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin: 18px 0;
                        padding: 10px 15px;
                        background: rgba(0,0,0,0.15);
                        border-radius: 8px;
                        border-left: 3px solid var(--primary);
                    }

                    .metric span:first-child {
                        font-weight: 500;
                        color: var(--text-muted);
                    }

                    .metric span:last-child {
                        font-family: 'Consolas', 'Courier New', monospace;
                        font-weight: 600;
                        padding: 4px 10px;
                        border-radius: 4px;
                        background: rgba(0,0,0,0.2);
                    }

                    .status-running {
                        color: var(--success);
                        animation: pulse 2s infinite;
                    }

                    .status-stopped {
                        color: var(--danger);
                    }

                    /* Controls styling */
                    .controls {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 15px;
                        margin: 25px 0;
                    }

                    .button {
                        padding: 12px 24px;
                        border-radius: 6px;
                        border: none;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        font-size: 14px;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        box-shadow: 0 3px 10px var(--shadow);
                    }

                    .button:hover {
                        transform: translateY(-3px);
                        box-shadow: 0 5px 15px var(--shadow);
                    }

                    .button:active {
                        transform: translateY(1px);
                    }

                    .start-button {
                        background-color: var(--success);
                        color: white;
                    }

                    .start-button:hover {
                        background-color: var(--primary-dark);
                    }

                    .stop-button {
                        background-color: var(--danger);
                        color: white;
                    }

                    .stop-button:hover {
                        background-color: var(--danger-dark);
                    }

                    .config-button {
                        background-color: var(--secondary);
                        color: white;
                    }

                    .config-button:hover {
                        background-color: var(--secondary-dark);
                    }

                    .console-button {
                        background-color: #9c27b0;
                        color: white;
                    }

                    .console-button:hover {
                        background-color: #7B1FA2;
                    }

                    /* Console styling */
                    .console-area, .config-area {
                        background: var(--dark-lighter);
                        border-radius: 12px;
                        padding: 20px;
                        margin: 25px 0;
                        border: 1px solid var(--dark-border);
                        box-shadow: 0 4px 15px var(--shadow);
                        display: none;
                    }

                    .console-output {
                        width: 100%;
                        height: 350px;
                        background: #1a1a1a;
                        color: #a5d6a7;
                        border: 1px solid var(--dark-border);
                        padding: 15px;
                        font-family: 'Consolas', 'Courier New', monospace;
                        overflow-y: auto;
                        white-space: pre-wrap;
                        line-height: 1.5;
                        font-size: 14px;
                        margin-bottom: 15px;
                        border-radius: 6px;
                    }

                    .console-input {
                        width: calc(100% - 110px);
                        background: #1a1a1a;
                        color: var(--text);
                        border: 1px solid var(--dark-border);
                        padding: 12px 15px;
                        font-family: 'Consolas', 'Courier New', monospace;
                        margin-top: 10px;
                        border-radius: 6px 0 0 6px;
                        font-size: 14px;
                        transition: all 0.3s ease;
                    }

                    .console-input:focus {
                        outline: none;
                        border-color: var(--primary);
                        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
                    }

                    .send-button {
                        width: 100px;
                        background-color: var(--warning);
                        color: white;
                        border-radius: 0 6px 6px 0;
                        margin-left: -1px;
                    }

                    .save-button {
                        background-color: var(--warning);
                        color: white;
                        margin-top: 15px;
                    }

                    textarea {
                        width: 100%;
                        height: 350px;
                        background: #1a1a1a;
                        color: var(--text);
                        border: 1px solid var(--dark-border);
                        padding: 15px;
                        font-family: 'Consolas', 'Courier New', monospace;
                        border-radius: 6px;
                        font-size: 14px;
                        line-height: 1.5;
                        transition: all 0.3s ease;
                    }

                    textarea:focus {
                        outline: none;
                        border-color: var(--primary);
                        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
                    }

                    /* Server list styling */
                    .server-list {
                        display: flex;
                        flex-direction: column;
                        gap: 15px;
                    }

                    .server-card {
                        background: var(--dark-lighter);
                        border-radius: 12px;
                        padding: 20px;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        border: 1px solid var(--dark-border);
                        box-shadow: 0 4px 10px var(--shadow);
                        position: relative;
                        overflow: hidden;
                    }

                    .server-card:hover {
                        background: var(--dark-medium);
                        transform: translateY(-3px);
                        box-shadow: 0 6px 20px var(--shadow);
                        border-color: var(--primary-dark);
                    }

                    .server-name {
                        font-size: 18px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    .server-path {
                        color: var(--text-muted);
                        font-size: 14px;
                        margin-top: 8px;
                        font-family: 'Consolas', 'Courier New', monospace;
                    }

                    .status-badge {
                        display: inline-block;
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                        text-transform: uppercase;
                    }

                    .status-badge.status-running {
                        background-color: rgba(76, 175, 80, 0.2);
                        color: var(--success);
                        border: 1px solid rgba(76, 175, 80, 0.3);
                    }

                    .status-badge.status-stopped {
                        background-color: rgba(244, 67, 54, 0.2);
                        color: var(--danger);
                        border: 1px solid rgba(244, 67, 54, 0.3);
                    }

                    /* Animations */
                    @keyframes pulse {
                        0% { opacity: 1; }
                        50% { opacity: 0.8; }
                        100% { opacity: 1; }
                    }

                    /* Custom scrollbar */
                    ::-webkit-scrollbar {
                        width: 10px;
                    }

                    ::-webkit-scrollbar-track {
                        background: var(--dark);
                        border-radius: 10px;
                    }

                    ::-webkit-scrollbar-thumb {
                        background: var(--dark-border);
                        border-radius: 10px;
                    }

                    ::-webkit-scrollbar-thumb:hover {
                        background: var(--primary-dark);
                    }

                    /* Responsive design */
                    @media (max-width: 768px) {
                        .controls {
                            flex-direction: column;
                        }
                        
                        .button {
                            width: 100%;
                            justify-content: center;
                        }
                        
                        .console-input {
                            width: 100%;
                            border-radius: 6px;
                            margin-bottom: 10px;
                        }
                        
                        .send-button {
                            width: 100%;
                            border-radius: 6px;
                            margin-left: 0;
                        }
                    }
                </style>
            </head>
            <body>
                <h1>Minecraft Server Manager</h1>
                <div class="server-list" id="serverList">
                    <!-- Server profiles will be loaded here -->
                </div>

                <script>
                    function loadServers() {
                        fetch('/api/servers')
                            .then(response => response.json())
                            .then(data => {
                                const serverList = document.getElementById('serverList');
                                serverList.innerHTML = '';
                                
                                if (data.servers.length === 0) {
                                    serverList.innerHTML = '<p>No server profiles found.</p>';
                                    return;
                                }
                                
                                data.servers.forEach(server => {
                                    const serverCard = document.createElement('div');
                                    serverCard.className = 'server-card';
                                    
                                    const statusClass = server.running ? 'status-running' : 'status-stopped';
                                    const statusText = server.running ? 'Running' : 'Stopped';
                                    
                                    serverCard.innerHTML = `
                                        <div class="server-name">
                                            ${server.name}
                                            <span class="status-badge ${statusClass}">${statusText}</span>
                                        </div>
                                        <div class="server-path">${server.path}</div>
                                    `;
                                    serverCard.addEventListener('click', () => {
                                        window.location.href = '/server?path=' + encodeURIComponent(server.path);
                                    });
                                    serverList.appendChild(serverCard);
                                });
                            });
                    }
                    
                    // Load servers immediately and refresh every 2 seconds
                    loadServers();
                    setInterval(loadServers, 2000);
                </script>
            </body>
            </html>
            """
            
        @app.route('/server')
        def server():
            """Show control panel for a specific server"""
            server_path = request.args.get('path')
            if not server_path or server_path not in self.profiles:
                return redirect('/')
                
            # Get the server name from path
            server_name = os.path.basename(server_path)
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Server: {server_name}</title>
                <style>
                    /* Modern UI Theme with Minecraft Inspiration */
                    :root {{
                        --primary: #4CAF50;
                        --primary-dark: #388E3C;
                        --primary-light: #81C784;
                        --secondary: #2196F3;
                        --secondary-dark: #1976D2;
                        --danger: #F44336;
                        --danger-dark: #D32F2F;
                        --warning: #FF9800;
                        --success: #4CAF50;
                        --dark: #212121;
                        --dark-lighter: #2d2d2d;
                        --dark-medium: #383838;
                        --dark-border: #444444;
                        --text: #f0f0f0;
                        --text-muted: #aaaaaa;
                        --shadow: rgba(0,0,0,0.2);
                    }}

                    body {{
                        background: var(--dark);
                        color: var(--text);
                        font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        line-height: 1.6;
                        background-image: linear-gradient(to bottom, #1a1a1a, #212121);
                        min-height: 100vh;
                        position: relative;
                        overflow-x: hidden;
                    }}

                    body::before {{
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 200px;
                        background-image: linear-gradient(to bottom, rgba(76, 175, 80, 0.05), transparent);
                        z-index: -1;
                    }}

                    h1, h2, h3 {{
                        font-weight: 600;
                        margin-top: 0;
                        color: var(--primary);
                        letter-spacing: 0.5px;
                    }}

                    h1 {{
                        font-size: 28px;
                        border-bottom: 2px solid var(--primary-dark);
                        padding-bottom: 10px;
                        margin-bottom: 25px;
                        display: inline-block;
                    }}

                    .header {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 30px;
                        padding-bottom: 15px;
                        border-bottom: 1px solid var(--dark-border);
                    }}

                    .back-button {{
                        background-color: var(--dark-medium);
                        color: var(--text);
                        border: none;
                        padding: 10px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        font-weight: 500;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        box-shadow: 0 2px 5px var(--shadow);
                    }}

                    .back-button:hover {{
                        background-color: var(--dark-border);
                        transform: translateY(-2px);
                    }}

                    .back-button::before {{
                        content: '←';
                        font-size: 18px;
                        line-height: 1;
                    }}

                    .status-card {{
                        background: var(--dark-lighter);
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        border: 1px solid var(--dark-border);
                        box-shadow: 0 4px 15px var(--shadow);
                        transition: all 0.3s ease;
                        position: relative;
                        overflow: hidden;
                    }}

                    .status-card:hover {{
                        transform: translateY(-3px);
                        box-shadow: 0 6px 20px var(--shadow);
                        border-color: var(--primary-dark);
                    }}

                    .status-card::after {{
                        content: '';
                        position: absolute;
                        top: 0;
                        right: 0;
                        width: 80px;
                        height: 80px;
                        background: linear-gradient(135deg, transparent 70%, rgba(76, 175, 80, 0.1) 100%);
                        border-radius: 0 0 0 80px;
                    }}

                    .metric {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin: 18px 0;
                        padding: 10px 15px;
                        background: rgba(0,0,0,0.15);
                        border-radius: 8px;
                        border-left: 3px solid var(--primary);
                    }}

                    .metric span:first-child {{
                        font-weight: 500;
                        color: var(--text-muted);
                    }}

                    .metric span:last-child {{
                        font-family: 'Consolas', 'Courier New', monospace;
                        font-weight: 600;
                        padding: 4px 10px;
                        border-radius: 4px;
                        background: rgba(0,0,0,0.2);
                    }}

                    .status-running {{
                        color: var(--success);
                        animation: pulse 2s infinite;
                    }}

                    .status-stopped {{
                        color: var(--danger);
                    }}

                    /* Controls styling */
                    .controls {{
                        display: flex;
                        flex-wrap: wrap;
                        gap: 15px;
                        margin: 25px 0;
                    }}

                    .button {{
                        padding: 12px 24px;
                        border-radius: 6px;
                        border: none;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        font-size: 14px;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        box-shadow: 0 3px 10px var(--shadow);
                    }}

                    .button:hover {{
                        transform: translateY(-3px);
                        box-shadow: 0 5px 15px var(--shadow);
                    }}

                    .button:active {{
                        transform: translateY(1px);
                    }}

                    .start-button {{
                        background-color: var(--success);
                        color: white;
                    }}

                    .start-button:hover {{
                        background-color: var(--primary-dark);
                    }}

                    .stop-button {{
                        background-color: var(--danger);
                        color: white;
                    }}

                    .stop-button:hover {{
                        background-color: var(--danger-dark);
                    }}

                    .config-button {{
                        background-color: var(--secondary);
                        color: white;
                    }}

                    .config-button:hover {{
                        background-color: var(--secondary-dark);
                    }}

                    .console-button {{
                        background-color: #9c27b0;
                        color: white;
                    }}

                    .console-button:hover {{
                        background-color: #7B1FA2;
                    }}

                    /* Console styling */
                    .console-area, .config-area {{
                        background: var(--dark-lighter);
                        border-radius: 12px;
                        padding: 20px;
                        margin: 25px 0;
                        border: 1px solid var(--dark-border);
                        box-shadow: 0 4px 15px var(--shadow);
                        display: none;
                    }}

                    .console-output {{
                        width: 100%;
                        height: 350px;
                        background: #1a1a1a;
                        color: #a5d6a7;
                        border: 1px solid var(--dark-border);
                        padding: 15px;
                        font-family: 'Consolas', 'Courier New', monospace;
                        overflow-y: auto;
                        white-space: pre-wrap;
                        line-height: 1.5;
                        font-size: 14px;
                        margin-bottom: 15px;
                        border-radius: 6px;
                    }}

                    .console-input {{
                        width: calc(100% - 110px);
                        background: #1a1a1a;
                        color: var(--text);
                        border: 1px solid var(--dark-border);
                        padding: 12px 15px;
                        font-family: 'Consolas', 'Courier New', monospace;
                        margin-top: 10px;
                        border-radius: 6px 0 0 6px;
                        font-size: 14px;
                        transition: all 0.3s ease;
                    }}

                    .console-input:focus {{
                        outline: none;
                        border-color: var(--primary);
                        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
                    }}

                    .send-button {{
                        width: 100px;
                        background-color: var(--warning);
                        color: white;
                        border-radius: 0 6px 6px 0;
                        margin-left: -1px;
                    }}

                    .save-button {{
                        background-color: var(--warning);
                        color: white;
                        margin-top: 15px;
                    }}

                    textarea {{
                        width: 100%;
                        height: 350px;
                        background: #1a1a1a;
                        color: var(--text);
                        border: 1px solid var (--dark-border);
                        padding: 15px;
                        font-family: 'Consolas', 'Courier New', monospace;
                        border-radius: 6px;
                        font-size: 14px;
                        line-height: 1.5;
                        transition: all 0.3s ease;
                    }}

                    textarea:focus {{
                        outline: none;
                        border-color: var(--primary);
                        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
                    }}

                    /* Animations */
                    @keyframes pulse {{
                        0% {{ opacity: 1; }}
                        50% {{ opacity: 0.8; }}
                        100% {{ opacity: 1; }}
                    }}

                    /* Custom scrollbar */
                    ::-webkit-scrollbar {{
                        width: 10px;
                    }}

                    ::-webkit-scrollbar-track {{
                        background: var(--dark);
                        border-radius: 10px;
                    }}

                    ::-webkit-scrollbar-thumb {{
                        background: var(--dark-border);
                        border-radius: 10px;
                    }}

                    ::-webkit-scrollbar-thumb:hover {{
                        background: var(--primary-dark);
                    }}

                    /* Responsive design */
                    @media (max-width: 768px) {{
                        .controls {{
                            flex-direction: column;
                        }}
                        
                        .button {{
                            width: 100%;
                            justify-content: center;
                        }}
                        
                        .console-input {{
                            width: 100%;
                            border-radius: 6px;
                            margin-bottom: 10px;
                        }}
                        
                        .send-button {{
                            width: 100%;
                            border-radius: 6px;
                            margin-left: 0;
                        }}
                    }}

                    /* Error message styling */
                    .error-message {{
                        background-color: rgba(244, 67, 54, 0.1);
                        border-left: 4px solid var(--danger);
                        color: var(--danger);
                        padding: 12px 15px;
                        margin: 10px 0;
                        border-radius: 4px;
                        font-weight: 500;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{server_name}</h1>
                    <button class="back-button" onclick="window.location.href='/'">Back to List</button>
                </div>

                <div class="status-card">
                    <h2>Server Status</h2>
                    <div class="metric">
                        <span>Status:</span>
                        <span id="serverStatus">Loading...</span>
                    </div>
                    <div class="metric">
                        <span>Path:</span>
                        <span>{server_path}</span>
                    </div>
                    <div class="metric">
                        <span>Memory Usage:</span>
                        <span id="memoryUsage">Checking...</span>
                    </div>
                </div>

                <div class="controls">
                    <button class="button start-button" id="startButton" onclick="startServer()">
                        <span class="button-icon">▶</span> Start Server
                    </button>
                    <button class="button stop-button" id="stopButton" onclick="stopServer()">
                        <span class="button-icon">■</span> Stop Server
                    </button>
                    <button class="button console-button" onclick="toggleConsole()">
                        <span class="button-icon">></span> Console
                    </button>
                    <button class="button config-button" onclick="toggleConfig()">
                        <span class="button-icon">⚙</span> Config
                    </button>
                </div>

                <div class="console-area" id="consoleArea">
                    <h2>Server Console</h2>
                    <div class="console-output" id="consoleOutput"></div>
                    <div style="display: flex;">
                        <input type="text" class="console-input" id="consoleInput" placeholder="Enter command..." onkeydown="if(event.key==='Enter') sendCommand()">
                        <button class="button send-button" onclick="sendCommand()">Send</button>
                    </div>
                </div>

                <div class="config-area" id="configArea">
                    <h2>Server Configuration</h2>
                    <textarea id="configText"></textarea>
                    <button class="button save-button" onclick="saveConfig()">Save Config</button>
                </div>

                <script>
                    // Server status and control
                    let serverStatus = 'unknown';
                    let consoleUpdateInterval;
                    
                    // Initial status check
                    checkServerStatus();
                    setInterval(checkServerStatus, 2000);
                    
                    function checkServerStatus() {{
                        fetch('/api/status?path={server_path}')
                            .then(response => response.json())
                            .then(data => {{
                                serverStatus = data.status;
                                const statusElement = document.getElementById('serverStatus');
                                
                                if (data.status === 'running') {{
                                    statusElement.textContent = 'Running';
                                    statusElement.className = 'status-running';
                                    document.getElementById('startButton').disabled = true;
                                    document.getElementById('stopButton').disabled = false;
                                }} else {{
                                    statusElement.textContent = 'Stopped';
                                    statusElement.className = 'status-stopped';
                                    document.getElementById('startButton').disabled = false;
                                    document.getElementById('stopButton').disabled = true;
                                }}
                                
                                // Update memory usage if available
                                if (data.memory) {{
                                    document.getElementById('memoryUsage').textContent = data.memory;
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error checking server status:', error);
                            }});
                    }}
                    
                    function startServer() {{
                        fetch('/api/control/start', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{ path: '{server_path}' }}),
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                // Enable console auto-update
                                if (!consoleUpdateInterval) {{
                                    consoleUpdateInterval = setInterval(updateConsole, 500);
                                }}
                                // Show console
                                document.getElementById('consoleArea').style.display = 'block';
                                // Update status will be handled by the status interval
                            }}
                        }})
                        .catch(error => console.error('Error:', error));
                    }}
                    
                    function stopServer() {{
                        fetch('/api/control/stop', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{ path: '{server_path}' }}),
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            // Status update will be handled by the status interval
                            console.log(data);
                        }})
                        .catch(error => console.error('Error:', error));
                    }}
                    
                    // Console functions
                    function toggleConsole() {{
                        const consoleArea = document.getElementById('consoleArea');
                        if (consoleArea.style.display === 'none' || consoleArea.style.display === '') {{
                            consoleArea.style.display = 'block';
                            // Start auto-update only if not already running
                            if (!consoleUpdateInterval) {{
                                consoleUpdateInterval = setInterval(updateConsole, 500);
                            }}
                            updateConsole(); // Immediate update
                        }} else {{
                            consoleArea.style.display = 'none';
                            // Stop auto-update
                            if (consoleUpdateInterval) {{
                                clearInterval(consoleUpdateInterval);
                                consoleUpdateInterval = null;
                            }}
                        }}
                    }}
                    
                    function updateConsole() {{
                        fetch('/api/console?path={server_path}')
                            .then(response => response.json())
                            .then(data => {{
                                const consoleOutput = document.getElementById('consoleOutput');
                                consoleOutput.innerHTML = data.lines.join('<br>');
                                consoleOutput.scrollTop = consoleOutput.scrollHeight;
                            }})
                            .catch(error => console.error('Error:', error));
                    }}
                    
                    function sendCommand() {{
                        const input = document.getElementById('consoleInput');
                        const command = input.value.trim();
                        
                        if (command) {{
                            fetch('/api/console/send', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/json',
                                }},
                                body: JSON.stringify({{ 
                                    path: '{server_path}',
                                    command: command
                                }}),
                            }})
                            .then(() => {{
                                input.value = '';
                                updateConsole(); // Refresh console after sending
                            }})
                            .catch(error => console.error('Error:', error));
                        }}
                    }}
                    
                    // Config functions
                    function toggleConfig() {{
                        const configArea = document.getElementById('configArea');
                        if (configArea.style.display === 'none' || configArea.style.display === '') {{
                            configArea.style.display = 'block';
                            loadConfig();
                        }} else {{
                            configArea.style.display = 'none';
                        }}
                    }}
                    
                    // Ensure this JavaScript function is correct in your HTML template
                    function loadConfig() {{
                        fetch('/api/config?path=' + encodeURIComponent('{server_path}'))
                            .then(response => response.json())
                            .then(data => {{
                                console.log("Config data:", data);  // Debug line
                                if (data.content) {{
                                    document.getElementById('configText').value = data.content;
                                }} else if (data.error) {{
                                    document.getElementById('configText').value = '# ' + data.error;
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error loading config:', error);
                                document.getElementById('configText').value = '# Error loading configuration';
                            }});
                    }}
                    
                    function saveConfig() {{
                        const configContent = document.getElementById('configText').value;
                        
                        fetch('/api/config/save', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{ 
                                path: '{server_path}',
                                content: configContent
                            }}),
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            alert(data.success ? 'Configuration saved successfully!' : 'Error saving configuration');
                        }})
                        .catch(error => console.error('Error:', error));
                    }}
                </script>
            </body>
            </html>
            """
            
        # API routes
        @app.route('/api/servers')
        def get_servers():
            servers = []
            for path, panel in self.profiles.items():
                # Check if server is running
                running = False
                if hasattr(panel, 'process') and panel.process:
                    try:
                        running = panel.process.state() == QProcess.Running and panel.process.processId() > 0
                    except:
                        running = False
                
                servers.append({
                    'path': path,
                    'name': os.path.basename(path),
                    'running': running
                })
            return jsonify({'servers': servers})
            
        @app.route('/api/status')
        def get_status():
            server_path = request.args.get('path')
            if not server_path or server_path not in self.profiles:
                return jsonify({'status': 'error', 'message': 'Invalid server path'})
                
            control_panel = self.profiles[server_path]
            if not hasattr(control_panel, 'process') or not control_panel.process:
                return jsonify({'status': 'stopped'})
                
            try:
                if control_panel.process.state() != QProcess.Running:
                    return jsonify({'status': 'stopped'})
                    
                pid = control_panel.process.processId()
                if pid <= 0:
                    return jsonify({'status': 'starting'})
                    
                proc = psutil.Process(pid)
                cpu = proc.cpu_percent()
                mem = proc.memory_info().rss / 1024 / 1024  # Convert to MB
                
                return jsonify({
                    'status': 'running',
                    'cpu': f"{cpu:.1f}%",
                    'memory': f"{mem:.1f} MB"
                })
            except Exception as e:
                return jsonify({'status': 'stopped', 'error': str(e)})
        
        @app.route('/api/console')
        def get_console():
            server_path = request.args.get('path')
            if not server_path or server_path not in self.console_buffers:
                return jsonify({'lines': []})
            
            # Look for active Java process if console buffer is empty
            if len(self.console_buffers[server_path].get_lines()) == 0:
                control_panel = self.profiles[server_path]
                if hasattr(control_panel, 'process') and control_panel.process:
                    if control_panel.process.state() == QProcess.Running:
                        self.console_buffers[server_path].add_line("Server is running... waiting for output")
            
            lines = self.console_buffers[server_path].get_lines()
            return jsonify({'lines': lines})
        
        @app.route('/api/console/send', methods=['POST'])
        def send_console_command():
            data = request.json
            server_path = data.get('path')
            command = data.get('command', '')
            
            if not server_path or server_path not in self.profiles:
                return jsonify({'success': False, 'message': 'Invalid server path'})
            
            if not command.strip():
                return jsonify({'success': False, 'message': 'Empty command'})
            
            try:
                # Emit signal to send command in main thread
                print(f"Emitting send_command_signal for {server_path}, command: {command}")
                self.process_handler.send_command_signal.emit(server_path, command)
                
                return jsonify({'success': True})
            except Exception as e:
                print(f"Error emitting command signal: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'Error sending command: {str(e)}'
                })
        
        @app.route('/api/control/start', methods=['POST'])
        def start_server():
            data = request.json
            server_path = data.get('path')
            
            if not server_path or server_path not in self.profiles:
                print(f"Invalid server path: {server_path}")
                return jsonify({'message': 'Invalid server path', 'success': False})
                
            try:
                # Emit signal to start server in main thread
                print(f"Emitting start_server_signal for {server_path}")
                self.process_handler.start_server_signal.emit(server_path)
                
                return jsonify({
                    'message': 'Server start requested...',
                    'success': True
                })
            except Exception as e:
                print(f"Error emitting start signal: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'message': f'Error starting server: {str(e)}',
                    'success': False
                })

        @app.route('/api/control/stop', methods=['POST'])
        def stop_server():
            data = request.json
            server_path = data.get('path')
            
            if not server_path or server_path not in self.profiles:
                return jsonify({'message': 'Invalid server path', 'success': False})
                
            try:
                # Emit signal to stop server in main thread
                print(f"Emitting stop_server_signal for {server_path}")
                self.process_handler.stop_server_signal.emit(server_path)
                
                return jsonify({
                    'message': 'Server stop requested...',
                    'success': True
                })
            except Exception as e:
                print(f"Error emitting stop signal: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'message': f'Error stopping server: {str(e)}',
                    'success': False
                })

        @app.route('/api/config/save', methods=['POST'])
        def save_config():
            """Save changes to the server.properties file"""
            data = request.json
            server_path = data.get('path')
            content = data.get('content')
            
            if not server_path or server_path not in self.profiles:
                return jsonify({'success': False, 'message': 'Invalid server path'})
            
            if content is None:
                return jsonify({'success': False, 'message': 'No content provided'})
            
            # Check if server is running
            control_panel = self.profiles[server_path]
            is_running = False
            if hasattr(control_panel, 'process') and control_panel.process:
                try:
                    is_running = control_panel.process.state() == QProcess.Running and control_panel.process.processId() > 0
                except:
                    is_running = False
            
            # Optionally warn if server is running
            # if is_running:
            #     return jsonify({'success': False, 'message': 'Cannot modify config while server is running'})
            
            try:
                config_path = os.path.join(server_path, 'server.properties')
                with open(config_path, 'w') as f:
                    f.write(content)
                
                print(f"Config saved for {server_path}")
                return jsonify({'success': True, 'message': 'Configuration saved successfully'})
            except Exception as e:
                error_msg = f"Error saving config: {str(e)}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'message': error_msg})

        @app.route('/api/config', methods=['GET'])
        def get_config():
            """Get the server.properties file content"""
            server_path = request.args.get('path')
            
            if not server_path or server_path not in self.profiles:
                return jsonify({'error': 'Invalid server path', 'content': ''})
            
            try:
                config_path = os.path.join(server_path, 'server.properties')
                print(f"Reading config from: {config_path}")
                
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        content = f.read()
                    print(f"Successfully read config ({len(content)} bytes)")
                    return jsonify({'content': content})
                else:
                    print(f"Config file not found: {config_path}")
                    return jsonify({'error': f'Config file not found: {config_path}', 'content': ''})
            except Exception as e:
                print(f"Error reading config: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Error reading config: {str(e)}', 'content': ''})
                
        return app

    def run_server(self):
        try:
            # Create app in the thread context
            app = self.setup_app()
            # Run app (this will block until the server is shut down)
            app.run(host='0.0.0.0', port=8080, debug=False)
        except Exception as e:
            print(f"WebUI server error: {e}")

    def start(self):
        if self.thread and self.thread.is_alive():
            return  # Already running
            
        self.running = True
        self.thread = threading.Thread(target=self.run_server)
        self.thread.daemon = True  # Make thread terminate when main process exits
        self.thread.start()
        
        # Wait a moment for server to start
        time.sleep(0.5)
        
        # Log that the server started with proper IP
        import socket
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
            print(f"WebUI started at http://{local_ip}:8080 and http://localhost:8080")
        except:
            print("WebUI started at http://localhost:8080")

    def stop(self):
        self.running = False
        # Flask doesn't offer a clean shutdown method
        # The thread will terminate when the application exits