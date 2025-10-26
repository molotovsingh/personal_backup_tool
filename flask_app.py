#!/usr/bin/env python3
"""
Flask Backup Manager - Entry Point

Run with:
    python flask_app.py
    or
    flask run
"""
import os
from flask_app import create_app, socketio

# Get configuration from environment
config_name = os.environ.get('FLASK_ENV', 'development')

# Create Flask app
app = create_app(config_name)

if __name__ == '__main__':
    # Run with SocketIO
    socketio.run(app,
                 host='0.0.0.0',
                 port=5001,  # Using 5001 as 5000 is used by AirPlay on macOS
                 debug=True,
                 use_reloader=True,
                 allow_unsafe_werkzeug=True)  # For development only
