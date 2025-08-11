#!/usr/bin/env python3
"""
WSGI entry point for production deployment
Compatible with Gunicorn and cloud deployment platforms
"""

import os
from server import app

# Set production environment
os.environ.setdefault('ENVIRONMENT', 'production')

# Configure application for production
application = app

# This makes the application callable by WSGI servers
if __name__ == "__main__":
    # This is for testing the WSGI app locally
    port = int(os.getenv('PORT', 5000))
    application.run(host='0.0.0.0', port=port)