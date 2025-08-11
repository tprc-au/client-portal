#!/usr/bin/env python3
"""
Production entry point for TPRC Portal
Optimized for cloud deployment with proper configuration
"""

import os
import sys
from server import app, logger

def main():
    """Main entry point for production deployment"""
    # Set production environment
    os.environ.setdefault('ENVIRONMENT', 'production')
    
    # Get port from environment (deployment platforms set this)
    port = int(os.getenv('PORT', 5000))
    
    # Production settings
    debug_mode = False
    
    # Log startup information
    logger.info(f"Starting TPRC Portal (Production) on port {port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'production')}")
    logger.info(f"Debug mode: {debug_mode}")
    
    # Production-optimized Flask settings
    app.config.update(
        DEBUG=False,
        TESTING=False,
        JSON_SORT_KEYS=False
    )
    
    # Start the server
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode,
        threaded=True,
        use_reloader=False
    )

if __name__ == '__main__':
    main()