#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

"""
WebSocket plugin integration for CherryPy
This file handles WebSocket setup and routing
"""

import os
import cherrypy
from headphones import logger

# Try to import WebSocket support
WEBSOCKET_AVAILABLE = False
try:
    from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
    from ws4py.websocket import WebSocket
    WEBSOCKET_AVAILABLE = True
    logger.info("WebSocket support is available")
except ImportError:
    logger.warning("WebSocket support not available. Install ws4py: pip install ws4py")
    WebSocketPlugin = None
    WebSocketTool = None
    WebSocket = None


def setup_websocket(cherrypy_instance=None):
    """
    Setup WebSocket plugin for CherryPy
    Call this function during server initialization
    """
    if not WEBSOCKET_AVAILABLE:
        logger.warning("WebSocket setup skipped - ws4py not installed")
        return False
    
    try:
        engine = getattr(cherrypy_instance, 'engine', None) if cherrypy_instance else None
        engine = engine or cherrypy.engine

        # Initialize WebSocket plugin on CherryPy engine
        WebSocketPlugin(engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()
        logger.info("WebSocket plugin initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to setup WebSocket: {e}")
        return False


def get_websocket_handler():
    """
    Get the WebSocket handler class
    Returns None if WebSocket is not available
    """
    if not WEBSOCKET_AVAILABLE:
        return None
    
    from headphones.websocket import WebSocketHandler
    return WebSocketHandler


def create_websocket_config():
    """
    Create CherryPy configuration for WebSocket endpoint
    """
    if not WEBSOCKET_AVAILABLE:
        return {}
    
    return {
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': get_websocket_handler()
        }
    }
