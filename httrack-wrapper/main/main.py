#!/usr/bin/env python3
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
from pathlib import Path
import webbrowser
import threading
import time

class HTTrackWrapper:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_routes()
        self.config_file = Path.home() / '.config' / 'httrack-wrapper' / 'config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_config()

    def load_config(self):
        """Load saved HTTrack configuration"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
        else:
            self.config = {
                'user_agent': 'Mozilla/5.0 (Android 10; Mobile; rv:121.0) Firefox/121.0',
                'max_depth': 5,
                'max_external_depth': 1,
                'max_size': '10M',
                'robots': True,
                'cookies': True,
                'update': False,
                'continue': False
            }

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>HTTrack Wrapper</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { 
                        font-family: Arial; 
                        padding: 15px; 
                        max-width: 800px; 
                        margin: 0 auto; 
                        background: #f5f5f5;
                    }
                    .container {
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .section {
                        margin: 15px 0;
                        padding: 15px;
                        border: 1px solid #eee;
                        border-radius: 4px;
                    }
                    label {
                        display: block;
                        margin: 10px 0 5px;
                    }
                    input[type="text"],
                    input[type="number"],
                    select {
                        width: 100%;
                        padding: 8px;
                        margin: 5px 0;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }
                    .checkbox-label {
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }
                    button {
                        background: #007bff;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                    }
                    button:hover {
                        background: #0056b3;
                    }
                    #status {
                        margin-top: 20px;
                        padding: 10px;
                        border-radius: 4px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>HTTrack Download Configuration</h2>
                    
                    <div class="section">
                        <label>Website URL:</label>
                        <input type="text" id="url" placeholder="https://example.com">
                        
                        <label>Output Directory:</label>
                        <input type="text" id="output" placeholder="downloads/example">
                    </div>

                    <div class="section">
                        <h3>Download Options</h3>
                        
                        <label>Maximum Depth:</label>
                        <input type="number" id="max_depth" value="5">
                        
                        <label>External Depth:</label>
                        <input type="number" id="max_external_depth" value="1">
                        
                        <label>Maximum File Size:</label>
                        <input type="text" id="max_size" value="10M">
                        
                        <div class="checkbox-label">
                            <input type="checkbox" id="robots" checked>
                            <label for="robots">Follow robots.txt rules</label>
                        </div>
                        
                        <div class="checkbox-label">
                            <input type="checkbox" id="cookies" checked>
                            <label for="cookies">Enable cookies</label>
                        </div>
                        
                        <div class="checkbox-label">
                            <input type="checkbox" id="update">
                            <label for="update">Update existing files</label>
                        </div>
                        
                        <div class="checkbox-label">
                            <input type="checkbox" id="continue">
                            <label for="continue">Continue interrupted download</label>
                        </div>
                    </div>

                    <button onclick="startDownload()">Start Download</button>
                    
                    <div id="status"></div>
                </div>

                <script>
                async function startDownload() {
                    const config = {
                        url: document.getElementById('url').value,
                        output: document.getElementById('output').value,
                        options: {
                            max_depth: document.getElementById('max_depth').value,
                            max_external_depth: document.getElementById('max_external_depth').value,
                            max_size: document.getElementById('max_size').value,
                            robots: document.getElementById('robots').checked,
                            cookies: document.getElementById('cookies').checked,
                            update: document.getElementById('update').checked,
                            continue: document.getElementById('continue').checked
                        }
                    };

                    const response = await fetch('/download', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(config)
                    });

                    const result = await response.json();
                    const status = document.getElementById('status');
                    status.textContent = result.message;
                    
                    if (result.needs_auth) {
                        status.textContent += "\nLogin required. Opening auth handler...";
                        window.open('http://127.0.0.1:10070', '_blank');
                    }
                }
                </script>
            </body>
            </html>
            """

        @self.app.route('/download', methods=['POST'])
        def start_download():
            data = request.json
            url = data['url']
            output = data['output']
            
            # Save configuration
            self.config.update(data['options'])
            self.save_config()
            
            # Check if login required
            analyzer = SiteAnalyzer()
            needs_auth, login_url = analyzer.check_login_required(url)
            
            if needs_auth:
                # Start auth handler if needed
                self.start_auth_handler(login_url)
                return jsonify({
                    'message': 'Login required for this site',
                    'needs_auth': True,
                    'login_url': login_url
                })
            
            # Generate and execute HTTrack command
            command = self.generate_command(url, output)
            return jsonify({
                'message': f'Starting download: {command}',
                'needs_auth': False
            })

    def generate_command(self, url: str, output: str) -> str:
        """Generate HTTrack command with current configuration"""
        options = [
            f'-O "{output}"',
            f'--user-agent "{self.config["user_agent"]}"',
            f'-r{self.config["max_depth"]}',
            f'-m{self.config["max_external_depth"]}',
            f'-M{self.config["max_size"]}'
        ]
        
        if not self.config['robots']:
            options.append('-s0')  # Ignore robots.txt
            
        if self.config['cookies']:
            options.append('-b0')  # Accept cookies
            
        if self.config['update']:
            options.append('-u')  # Update existing files
            
        if self.config['continue']:
            options.append('-c')  # Continue interrupted download

        # Check if we have auth data
        auth_file = Path.home() / '.config' / 'httrack-wrapper' / 'auth_data.json'
        if auth_file.exists():
            with open(auth_file) as f:
                auth_data = json.load(f)
                if auth_data.get('cookies'):
                    cookie_str = '; '.join(f'{k}={v}' for k, v in auth_data['cookies'].items())
                    options.append(f'--cookies "{cookie_str}"')

        return f"httrack {url} {' '.join(options)}"

    def save_config(self):
        """Save current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def start_auth_handler(self, login_url: str):
        """Start the auth handler on a different port"""
        if not hasattr(self, 'auth_handler'):
            from auth_handler import AuthHandler  # Separate module
            self.auth_handler = AuthHandler()
            auth_thread = threading.Thread(
                target=self.auth_handler.run,
                kwargs={'host': '127.0.0.1', 'port': 10070}
            )
            auth_thread.daemon = True
            auth_thread.start()

    def run(self, host='127.0.0.1', port=10069):
        print(f"""
        🚀 HTTrack Wrapper Started!
        
        1. Open http://{host}:{port} in your browser
        2. Configure download options
        3. Enter URL and start download
        4. Auth handler will open if login required
        
        Press Ctrl+C to stop
        """)
        
        self.app.run(host=host, port=port)

class SiteAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:121.0) Firefox/121.0'
        })

    def check_login_required(self, url: str) -> tuple[bool, str]:
        """Check if site requires login"""
        try:
            response = self.session.get(url, allow_redirects=True)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Quick checks for common login walls
            login_indicators = [
                ('/login', '/signin', '/auth'),  # URLs
                ('login required', 'please sign in', 'create account'),  # Text
                ('input[type="password"]', 'form[action*="login"]')  # Elements
            ]
            
            # Check URL
            if any(x in response.url.lower() for x in login_indicators[0]):
                return True, response.url

            # Check page text
            text = soup.get_text().lower()
            if any(x in text for x in login_indicators[1]):
                return True, url

            # Check for login forms
            for selector in login_indicators[2]:
                if soup.select(selector):
                    return True, url

            return False, url

        except Exception as e:
            print(f"Error checking login requirement: {e}")
            return False, url

def main():
    import argparse
    parser = argparse.ArgumentParser(description='HTTrack Wrapper with Auth Detection')
    parser.add_argument('--url', help='URL to download')
    parser.add_argument('--output', help='Output directory')
    args = parser.parse_args()

    wrapper = HTTrackWrapper()
    
    if args.url and args.output:
        # Direct command line usage
        analyzer = SiteAnalyzer()
        needs_auth, login_url = analyzer.check_login_required(args.url)
        
        if needs_auth:
            print("Login required. Starting auth handler...")
            wrapper.start_auth_handler(login_url)
            input("Press Enter after completing authentication...")
        
        command = wrapper.generate_command(args.url, args.output)
        print(f"Executing: {command}")
        import subprocess
        subprocess.run(command, shell=True)
    else:
        # Start web interface
        wrapper.run()

if __name__ == "__main__":
    main()
