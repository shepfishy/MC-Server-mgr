from flask import Flask, render_template, jsonify, send_from_directory, request, redirect
import os
import psutil
import threading
import time
from PyQt5.QtCore import QProcess, pyqtSignal, QObject
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

class WebUIManager:
    """Central manager for the web UI interface"""
    def __init__(self):
        self.app = None
        self.thread = None
        self.running = False
        self.profiles = {}  # Dictionary of server paths to ServerControlPanel objects
        self.console_buffers = {}  # Dictionary of server paths to console buffers
        
    def add_server_profile(self, server_path, control_panel):
        """Register a server profile with the web UI"""
        self.profiles[server_path] = control_panel
        self.console_buffers[server_path] = ConsoleBuffer(500)
        
        # Connect signals for console output
        if hasattr(control_panel, 'process'):
            control_panel.process.readyReadStandardOutput.connect(
                lambda: self.capture_stdout(server_path)
            )
            control_panel.process.readyReadStandardError.connect(
                lambda: self.capture_stderr(server_path)
            )
    
    def capture_stdout(self, server_path):
        """Capture stdout from server process"""
        if server_path in self.profiles:
            control_panel = self.profiles[server_path]
            if hasattr(control_panel, 'process') and control_panel.process:
                data = control_panel.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
                for line in data.splitlines():
                    if line.strip():
                        self.console_buffers[server_path].add_line(line)
    
    def capture_stderr(self, server_path):
        """Capture stderr from server process"""
        if server_path in self.profiles:
            control_panel = self.profiles[server_path]
            if hasattr(control_panel, 'process') and control_panel.process:
                data = control_panel.process.readAllStandardError().data().decode('utf-8', errors='replace')
                for line in data.splitlines():
                    if line.strip():
                        self.console_buffers[server_path].add_line(f"[ERROR] {line}")

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
                    body {
                        background: #212121;
                        color: #f0f0f0;
                        font-family: Arial, sans-serif;
                        margin: 20px;
                    }
                    h1 {
                        color: #4caf50;
                        margin-bottom: 20px;
                    }
                    .server-list {
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                    }
                    .server-card {
                        background: #2d2d2d;
                        border-radius: 8px;
                        padding: 15px;
                        cursor: pointer;
                        transition: background 0.2s;
                    }
                    .server-card:hover {
                        background: #3d3d3d;
                    }
                    .server-name {
                        font-size: 1.2em;
                        font-weight: bold;
                    }
                    .server-path {
                        color: #aaa;
                        font-size: 0.9em;
                        margin-top: 5px;
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
                                    serverCard.innerHTML = `
                                        <div class="server-name">${server.name}</div>
                                        <div class="server-path">${server.path}</div>
                                    `;
                                    serverCard.addEventListener('click', () => {
                                        window.location.href = '/server?path=' + encodeURIComponent(server.path);
                                    });
                                    serverList.appendChild(serverCard);
                                });
                            });
                    }
                    
                    loadServers();
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
                    body {{
                        background: #212121;
                        color: #f0f0f0;
                        font-family: Arial, sans-serif;
                        margin: 20px;
                    }}
                    .header {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 20px;
                    }}
                    .back-button {{
                        background-color: #555;
                        color: white;
                        border: none;
                        padding: 8px 12px;
                        border-radius: 4px;
                        cursor: pointer;
                    }}
                    .status-card {{
                        background: #2d2d2d;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 10px 0;
                    }}
                    .metric {{
                        display: flex;
                        justify-content: space-between;
                        margin: 10px 0;
                    }}
                    .status-running {{
                        color: #4caf50;
                    }}
                    .status-stopped {{
                        color: #f44336;
                    }}
                    .controls {{
                        display: flex;
                        gap: 10px;
                        margin: 20px 0;
                    }}
                    .button {{
                        padding: 10px 15px;
                        border-radius: 4px;
                        border: none;
                        font-weight: bold;
                        cursor: pointer;
                    }}
                    .button:disabled {{
                        opacity: 0.5;
                        cursor: not-allowed;
                    }}
                    .start-button {{
                        background-color: #4caf50;
                        color: white;
                    }}
                    .stop-button {{
                        background-color: #f44336;
                        color: white;
                    }}
                    .config-button {{
                        background-color: #2196f3;
                        color: white;
                    }}
                    .console-button {{
                        background-color: #9c27b0;
                        color: white;
                    }}
                    .config-area, .console-area {{
                        background: #2d2d2d;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                        display: none;
                    }}
                    textarea {{
                        width: 100%;
                        height: 300px;
                        background: #1a1a1a;
                        color: #f0f0f0;
                        border: 1px solid #444;
                        padding: 8px;
                        font-family: monospace;
                    }}
                    .console-output {{
                        width: 100%;
                        height: 300px;
                        background: #1a1a1a;
                        color: #f0f0f0;
                        border: 1px solid #444;
                        padding: 8px;
                        font-family: monospace;
                        overflow-y: auto;
                        white-space: pre-wrap;
                    }}
                    .console-input {{
                        width: calc(100% - 100px);
                        background: #1a1a1a;
                        color: #f0f0f0;
                        border: 1px solid #444;
                        padding: 8px;
                        font-family: monospace;
                        margin-top: 10px;
                    }}
                    .send-button {{
                        width: 80px;
                        background-color: #ff9800;
                        color: white;
                        margin-left: 10px;
                    }}
                    .save-button {{
                        background-color: #ff9800;
                        color: white;
                        margin-top: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{server_name}</h1>
                    <button onclick="window.location.href='/'" class="back-button">← Back to Servers</button>
                </div>
                
                <div class="controls">
                    <button id="startBtn" class="button start-button">Start Server</button>
                    <button id="stopBtn" class="button stop-button">Stop Server</button>
                    <button id="configBtn" class="button config-button">Edit Config</button>
                    <button id="consoleBtn" class="button console-button">Console</button>
                </div>
                
                <div class="status-card">
                    <div class="metric">
                        <span>Status:</span>
                        <span id="status"></span>
                    </div>
                    <div class="metric">
                        <span>CPU Usage:</span>
                        <span id="cpu"></span>
                    </div>
                    <div class="metric">
                        <span>Memory Usage:</span>
                        <span id="memory"></span>
                    </div>
                </div>
                
                <div id="configArea" class="config-area">
                    <h2>Server Properties</h2>
                    <textarea id="configText"></textarea>
                    <button id="saveConfig" class="button save-button">Save Config</button>
                </div>
                
                <div id="consoleArea" class="console-area">
                    <h2>Server Console</h2>
                    <div id="consoleOutput" class="console-output"></div>
                    <div style="display: flex; margin-top: 10px;">
                        <input type="text" id="consoleInput" class="console-input" placeholder="Type command...">
                        <button id="sendCommand" class="button send-button">Send</button>
                    </div>
                </div>

                <script>
                    const serverPath = "{server_path}";
                    let serverRunning = false;
                    let consoleUpdateInterval;
                    
                    function updateStatus() {{
                        fetch(`/api/status?path=${{encodeURIComponent(serverPath)}}`)
                            .then(response => response.json())
                            .then(data => {{
                                document.getElementById('status').textContent = data.status;
                                document.getElementById('status').className = 
                                    data.status === 'running' ? 'status-running' : 'status-stopped';
                                document.getElementById('cpu').textContent = data.cpu || 'N/A';
                                document.getElementById('memory').textContent = data.memory || 'N/A';
                                
                                serverRunning = data.status === 'running';
                                updateButtons();
                            }});
                    }}
                    
                    function updateButtons() {{
                        document.getElementById('startBtn').disabled = serverRunning;
                        document.getElementById('stopBtn').disabled = !serverRunning;
                    }}
                    
                    // Console functions
                    function updateConsole() {{
                        if (document.getElementById('consoleArea').style.display === 'block') {{
                            fetch(`/api/console?path=${{encodeURIComponent(serverPath)}}`)
                                .then(response => response.json())
                                .then(data => {{
                                    const consoleOutput = document.getElementById('consoleOutput');
                                    consoleOutput.innerHTML = '';
                                    
                                    data.lines.forEach(line => {{
                                        const lineElement = document.createElement('div');
                                        lineElement.textContent = line;
                                        consoleOutput.appendChild(lineElement);
                                    }});
                                    
                                    // Auto-scroll to bottom
                                    consoleOutput.scrollTop = consoleOutput.scrollHeight;
                                }});
                        }}
                    }}
                    
                    document.getElementById('consoleBtn').addEventListener('click', function() {{
                        const consoleArea = document.getElementById('consoleArea');
                        const configArea = document.getElementById('configArea');
                        
                        configArea.style.display = 'none';
                        
                        if (consoleArea.style.display === 'block') {{
                            consoleArea.style.display = 'none';
                            clearInterval(consoleUpdateInterval);
                        }} else {{
                            consoleArea.style.display = 'block';
                            updateConsole();
                            consoleUpdateInterval = setInterval(updateConsole, 1000);
                        }}
                    }});
                    
                    document.getElementById('sendCommand').addEventListener('click', sendConsoleCommand);
                    document.getElementById('consoleInput').addEventListener('keypress', function(e) {{
                        if (e.key === 'Enter') {{
                            sendConsoleCommand();
                        }}
                    }});
                    
                    function sendConsoleCommand() {{
                        const commandInput = document.getElementById('consoleInput');
                        const command = commandInput.value;
                        
                        if (command.trim() === '') return;
                        
                        fetch('/api/console/send', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                command: command,
                                path: serverPath
                            }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (!data.success) {{
                                alert(data.message);
                            }}
                            commandInput.value = '';
                            updateConsole();
                        }});
                    }}
                    
                    document.getElementById('startBtn').addEventListener('click', function() {{
                        fetch('/api/control/start', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                path: serverPath
                            }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            alert(data.message);
                            updateStatus();
                        }});
                    }});
                    
                    document.getElementById('stopBtn').addEventListener('click', function() {{
                        fetch('/api/control/stop', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                path: serverPath
                            }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            alert(data.message);
                            updateStatus();
                        }});
                    }});
                    
                    document.getElementById('configBtn').addEventListener('click', function() {{
                        const configArea = document.getElementById('configArea');
                        const consoleArea = document.getElementById('consoleArea');
                        
                        consoleArea.style.display = 'none';
                        clearInterval(consoleUpdateInterval);
                        
                        if (configArea.style.display === 'block') {{
                            configArea.style.display = 'none';
                            return;
                        }}
                        
                        configArea.style.display = 'block';
                        
                        fetch('/api/config?path=' + encodeURIComponent(serverPath))
                            .then(response => response.text())
                            .then(data => {{
                                document.getElementById('configText').value = data;
                            }});
                    }});
                    
                    document.getElementById('saveConfig').addEventListener('click', function() {{
                        const configText = document.getElementById('configText').value;
                        
                        fetch('/api/config', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                config: configText,
                                path: serverPath
                            }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            alert(data.message);
                        }});
                    }});
                    
                    // Update status every second
                    setInterval(updateStatus, 1000);
                    updateStatus();
                </script>
            </body>
            </html>
            """
            
        # API routes
        @app.route('/api/servers')
        def get_servers():
            servers = []
            for path, panel in self.profiles.items():
                servers.append({
                    'path': path,
                    'name': os.path.basename(path)
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
                
            lines = self.console_buffers[server_path].get_lines()
            return jsonify({'lines': lines})
        
        @app.route('/api/console/send', methods=['POST'])
        def send_console_command():
            data = request.json
            server_path = data.get('path')
            command = data.get('command', '')
            
            if not server_path or server_path not in self.profiles:
                return jsonify({'success': False, 'message': 'Invalid server path'})
                
            control_panel = self.profiles[server_path]
            if not hasattr(control_panel, 'process') or not control_panel.process or control_panel.process.state() != QProcess.Running:
                return jsonify({'success': False, 'message': 'Server is not running'})
                
            try:
                if command:
                    control_panel.process.write(f"{command}\n".encode('utf-8'))
                    self.console_buffers[server_path].add_line(f"> {command}")
                    return jsonify({'success': True})
                return jsonify({'success': False, 'message': 'Empty command'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'Error: {str(e)}'})
        
        @app.route('/api/control/start', methods=['POST'])
        def start_server():
            data = request.json
            server_path = data.get('path')
            
            if not server_path or server_path not in self.profiles:
                return jsonify({'message': 'Invalid server path'})
                
            control_panel = self.profiles[server_path]
            if not hasattr(control_panel, 'start_from_web'):
                return jsonify({'message': 'Server cannot be started from web UI'})
                
            if hasattr(control_panel, 'process') and control_panel.process and control_panel.process.state() == QProcess.Running:
                return jsonify({'message': 'Server is already running'})
                
            try:
                # Call the panel's start method
                result = control_panel.start_from_web()
                if result:
                    return jsonify({'message': 'Server is starting...'})
                else:
                    return jsonify({'message': 'Server could not be started'})
            except Exception as e:
                return jsonify({'message': f'Error starting server: {str(e)}'})
                
        @app.route('/api/control/stop', methods=['POST'])
        def stop_server():
            data = request.json
            server_path = data.get('path')
            
            if not server_path or server_path not in self.profiles:
                return jsonify({'message': 'Invalid server path'})
                
            control_panel = self.profiles[server_path]
            if hasattr(control_panel, 'process') and control_panel.process and control_panel.process.state() == QProcess.Running:
                # Gracefully stop server
                control_panel.process.write(b"stop\n")
                return jsonify({'message': 'Server is shutting down...'})
            else:
                return jsonify({'message': 'Server is not running'})
                
        @app.route('/api/config', methods=['GET', 'POST'])
        def config():
            if request.method == 'GET':
                server_path = request.args.get('path')
                if not server_path or server_path not in self.profiles:
                    return "# Invalid server path"
                    
                config_path = os.path.join(server_path, 'server.properties')
                try:
                    with open(config_path, 'r') as file:
                        return file.read()
                except Exception as e:
                    return f"# Error loading config: {str(e)}"
            else:
                data = request.json
                server_path = data.get('path')
                config_data = data.get('config', '')
                
                if not server_path or server_path not in self.profiles:
                    return jsonify({'message': 'Invalid server path'})
                    
                control_panel = self.profiles[server_path]
                if hasattr(control_panel, 'process') and control_panel.process and control_panel.process.state() == QProcess.Running:
                    return jsonify({'message': 'Cannot modify config while server is running'})
                    
                config_path = os.path.join(server_path, 'server.properties')
                try:
                    with open(config_path, 'w') as file:
                        file.write(config_data)
                        
                    return jsonify({'message': 'Configuration saved successfully'})
                except Exception as e:
                    return jsonify({'message': f'Error saving config: {str(e)}'})
                
        return app

    def run_server(self):
        try:
            # Create app in the thread context
            app = self.setup_app()
            # Run app (this will block until the server is shut down)
            app.run(host='127.0.0.1', port=8080, debug=False)
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
        
        # Log that the server started
        print("WebUI started at http://localhost:8080")

    def stop(self):
        self.running = False
        # Flask doesn't offer a clean shutdown method
        # The thread will terminate when the application exits