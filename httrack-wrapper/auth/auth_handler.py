#!/usr/bin/env python3
from flask import Flask, request, jsonify
import json
from pathlib import Path

class AuthHandler:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_routes()
        self.auth_file = Path.home() / '.config' / 'httrack-wrapper' / 'auth_data.json'

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Auth Handler</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { 
                        font-family: Arial; 
                        padding: 15px; 
                        max-width: 600px; 
                        margin: 0 auto; 
                    }
                    .field {
                        margin: 10px 0;
                    }
                    input {
                        width: 100%;
                        padding: 8px;
                        margin: 5px 0;
                    }
                    button {
                        width: 100%;
                        padding: 10px;
                        background: #007bff;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    }
                </style>
            </head>
            <body>
                <div class="field">
                    <input type="text" id="username" placeholder="Username/Email">
                </div>
                <div class="field">
                    <input type="password" id="password" placeholder="Password">
                </div>
                <div class="field" id="tfaField" style="display:none">
                    <input type="text" id="tfa" placeholder="2FA Code" maxlength="6">
                </div>
                <button onclick="submitAuth()">Submit</button>

                <script>
                async function submitAuth() {
                    const auth = {
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value,
                        tfa: document.getElementById('tfa').value
                    };

                    const response = await fetch('/auth', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(auth)
                    });

                    const result = await response.json();
                    if (result.success) {
                        window.close();  // Close auth window
                    }
                }

                // Add function to check for 2FA field
                function show2FAField() {
                    const tfaField = document.getElementById('tfaField');
                    tfaField.style.display = 'block';
                }
                </script>                
                
            

            </body>
            </html>
            """

        @self.app.route('/auth', methods=['POST'])
        def handle_auth():
            auth_data = request.json
            
            # Save auth data
            self.save_auth(auth_data)
            
            return jsonify({
                'success': True,
                'message': 'Auth data saved, you can close this window'
            })

        @self.app.route('/check-2fa', methods=['POST'])
        def check_2fa():
            """Endpoint to check if 2FA is required after initial login"""
            url = request.json.get('url')
            # Here you could implement actual 2FA detection logic
            return jsonify({'requires_2fa': False})

    def save_auth(self, auth_data: dict):
        """Save authentication data"""
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.auth_file, 'w') as f:
            json.dump(auth_data, f, indent=2)

    def run(self, host='127.0.0.1', port=10070):
        self.app.run(host=host, port=port)

