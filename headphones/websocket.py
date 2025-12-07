#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

"""
WebSocket server for real-time notifications
"""

import json
import threading
import time
from collections import defaultdict
from headphones import logger


class WebSocketHandler:
    """WebSocket handler using CherryPy WebSocket plugin"""
    
    def __init__(self, sock):
        self.sock = sock
        WebSocketManager.register_client(self)
        logger.info("WebSocket client connected")

    def received_message(self, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(str(message))
            logger.debug(f"WebSocket received: {data}")
            
            # Handle different message types
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                self.send_message('pong', {'timestamp': time.time()})
            elif msg_type == 'subscribe':
                # Client can subscribe to specific event types
                pass
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def closed(self, code, reason=None):
        """Handle WebSocket connection closed"""
        WebSocketManager.unregister_client(self)
        logger.info(f"WebSocket client disconnected: {code} - {reason}")

    def send_message(self, msg_type, data):
        """Send message to client"""
        try:
            message = json.dumps({
                'type': msg_type,
                'data': data,
                'timestamp': time.time()
            })
            self.sock.send(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")


class WebSocketManager:
    """Manages all WebSocket connections and broadcasts"""
    
    clients = []
    lock = threading.Lock()
    
    @classmethod
    def register_client(cls, client):
        """Register a new WebSocket client"""
        with cls.lock:
            cls.clients.append(client)
            logger.info(f"WebSocket clients: {len(cls.clients)}")
    
    @classmethod
    def unregister_client(cls, client):
        """Unregister a WebSocket client"""
        with cls.lock:
            if client in cls.clients:
                cls.clients.remove(client)
            logger.info(f"WebSocket clients: {len(cls.clients)}")
    
    @classmethod
    def broadcast(cls, msg_type, data):
        """Broadcast message to all connected clients"""
        with cls.lock:
            disconnected = []
            for client in cls.clients:
                try:
                    client.send_message(msg_type, data)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")
                    disconnected.append(client)
            
            # Remove disconnected clients
            for client in disconnected:
                if client in cls.clients:
                    cls.clients.remove(client)
    
    @classmethod
    def notify_download_started(cls, artist_name, album_title):
        """Notify clients that a download has started"""
        cls.broadcast('download_started', {
            'artist': artist_name,
            'album': album_title,
            'message': f'Started downloading: {artist_name} - {album_title}'
        })
    
    @classmethod
    def notify_download_completed(cls, artist_name, album_title):
        """Notify clients that a download has completed"""
        cls.broadcast('download_completed', {
            'artist': artist_name,
            'album': album_title,
            'message': f'Completed download: {artist_name} - {album_title}'
        })
    
    @classmethod
    def notify_artist_added(cls, artist_name, artist_id):
        """Notify clients that an artist was added"""
        cls.broadcast('artist_added', {
            'artist': artist_name,
            'artistId': artist_id,
            'message': f'Added artist: {artist_name}'
        })
    
    @classmethod
    def notify_album_wanted(cls, artist_name, album_title):
        """Notify clients that an album is wanted"""
        cls.broadcast('album_wanted', {
            'artist': artist_name,
            'album': album_title,
            'message': f'Marked as wanted: {artist_name} - {album_title}'
        })
    
    @classmethod
    def notify_search_started(cls):
        """Notify clients that a search has started"""
        cls.broadcast('search_started', {
            'message': 'Search started'
        })
    
    @classmethod
    def notify_search_completed(cls, results_count):
        """Notify clients that a search has completed"""
        cls.broadcast('search_completed', {
            'resultsCount': results_count,
            'message': f'Search completed: {results_count} results'
        })
    
    @classmethod
    def notify_error(cls, error_message):
        """Notify clients of an error"""
        cls.broadcast('error', {
            'message': error_message
        })
    
    @classmethod
    def notify_info(cls, info_message):
        """Notify clients with info message"""
        cls.broadcast('info', {
            'message': info_message
        })


# Helper function to be called from other parts of the application
def notify_websocket(event_type, **kwargs):
    """
    Helper function to send WebSocket notifications from anywhere in the app
    
    Usage:
        from headphones.websocket import notify_websocket
        notify_websocket('download_started', artist='Artist Name', album='Album Title')
    """
    method_name = f"notify_{event_type}"
    if hasattr(WebSocketManager, method_name):
        method = getattr(WebSocketManager, method_name)
        method(**kwargs)
    else:
        logger.warning(f"Unknown WebSocket event type: {event_type}")
