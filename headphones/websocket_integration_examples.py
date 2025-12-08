"""
Exemple d'intégration des notifications WebSocket dans Headphones

Ce fichier montre comment ajouter des notifications WebSocket
dans les différentes parties du code Headphones.
"""

# ==========================================
# Exemple 1: Dans searcher.py
# ==========================================

def searchforalbum_example(albumid=None):
    """Exemple d'intégration dans la fonction de recherche"""
    from headphones.websocket import notify_websocket
    import headphones
    
    myDB = headphones.db.DBConnection()
    
    # Notifier le début de la recherche
    notify_websocket('search_started')
    
    try:
        # ... code de recherche existant ...
        
        # Supposons qu'on trouve des résultats
        results = []  # Résultats de recherche
        
        # Notifier la fin de la recherche
        notify_websocket('search_completed', results_count=len(results))
        
        return results
        
    except Exception as e:
        # Notifier l'erreur
        notify_websocket('error', error_message=f'Search failed: {str(e)}')
        raise


# ==========================================
# Exemple 2: Dans importer.py
# ==========================================

def addArtisttoDB_example(artistid):
    """Exemple d'intégration dans l'ajout d'artiste"""
    from headphones.websocket import notify_websocket
    import headphones
    
    try:
        # ... code d'ajout existant ...
        
        # Supposons qu'on a ajouté l'artiste
        artist_name = "Example Artist"  # Récupéré depuis MusicBrainz
        
        # Notifier l'ajout
        notify_websocket('artist_added', 
                        artist=artist_name, 
                        artist_id=artistid)
        
        # Envoyer aussi une notification info
        notify_websocket('info', 
                        info_message=f'Successfully added {artist_name}')
        
    except Exception as e:
        notify_websocket('error', 
                        error_message=f'Failed to add artist: {str(e)}')
        raise


# ==========================================
# Exemple 3: Dans postprocessor.py
# ==========================================

def processAlbum_example(album_path):
    """Exemple d'intégration dans le post-traitement"""
    from headphones.websocket import notify_websocket
    import headphones
    
    myDB = headphones.db.DBConnection()
    
    try:
        # Récupérer les infos de l'album
        # ... code existant ...
        
        artist_name = "Example Artist"
        album_title = "Example Album"
        
        # Notifier le début du traitement
        notify_websocket('info', 
                        info_message=f'Processing {artist_name} - {album_title}')
        
        # ... code de traitement ...
        
        # Notifier la fin du traitement
        notify_websocket('download_completed',
                        artist=artist_name,
                        album=album_title)
        
    except Exception as e:
        notify_websocket('error',
                        error_message=f'Post-processing failed: {str(e)}')
        raise


# ==========================================
# Exemple 4: Dans librarysync.py
# ==========================================

def libraryScan_example():
    """Exemple d'intégration dans le scan de bibliothèque"""
    from headphones.websocket import notify_websocket
    import headphones
    
    # Notifier le début du scan
    notify_websocket('info', info_message='Library scan started')
    
    try:
        # ... code de scan existant ...
        
        added_count = 0
        updated_count = 0
        
        # ... traitement ...
        
        # Notifier la fin du scan
        notify_websocket('info', 
                        info_message=f'Library scan completed: {added_count} added, {updated_count} updated')
        
    except Exception as e:
        notify_websocket('error',
                        error_message=f'Library scan failed: {str(e)}')
        raise


# ==========================================
# Exemple 5: Notifications personnalisées
# ==========================================

def custom_notification_example():
    """Exemple de notification personnalisée"""
    from headphones.websocket import WebSocketManager
    
    # Broadcast direct avec données personnalisées
    WebSocketManager.broadcast('custom_event', {
        'title': 'Custom Event',
        'description': 'This is a custom notification',
        'priority': 'high',
        'data': {
            'key1': 'value1',
            'key2': 'value2'
        }
    })


# ==========================================
# Exemple 6: Dans un thread de téléchargement
# ==========================================

def download_thread_example(nzb_url, album_info):
    """Exemple dans un thread de téléchargement"""
    from headphones.websocket import notify_websocket
    import time
    
    artist = album_info['artist']
    album = album_info['album']
    
    try:
        # Notifier le début
        notify_websocket('download_started', artist=artist, album=album)
        
        # Simuler le téléchargement
        time.sleep(5)
        
        # Notifier le succès
        notify_websocket('download_completed', artist=artist, album=album)
        
    except Exception as e:
        notify_websocket('error', 
                        error_message=f'Download failed for {artist} - {album}: {str(e)}')


# ==========================================
# Exemple 7: Intégration avec les notifiers existants
# ==========================================

def send_notification_wrapper(message, event='info'):
    """
    Wrapper pour envoyer à la fois les notifications classiques
    et les notifications WebSocket
    """
    from headphones.websocket import notify_websocket
    from headphones import notifiers
    
    # Envoyer via les notifiers classiques (email, Prowl, etc.)
    notifiers.notify(event, message)
    
    # Envoyer via WebSocket pour le frontend moderne
    if event == 'download_complete':
        # Parser le message pour extraire artiste et album
        # Format attendu: "Artist - Album downloaded"
        parts = message.split(' - ')
        if len(parts) >= 2:
            artist = parts[0]
            album = parts[1].replace(' downloaded', '')
            notify_websocket('download_completed', artist=artist, album=album)
    else:
        notify_websocket(event, info_message=message)


# ==========================================
# Instructions d'utilisation
# ==========================================

"""
Pour intégrer ces notifications dans votre code:

1. Importer la fonction notify_websocket:
   from headphones.websocket import notify_websocket

2. Appeler la fonction aux endroits appropriés:
   notify_websocket('event_type', **kwargs)

3. Types d'événements disponibles:
   - download_started: artist, album
   - download_completed: artist, album
   - artist_added: artist, artist_id
   - album_wanted: artist, album
   - search_started: (pas de paramètres)
   - search_completed: results_count
   - error: error_message
   - info: info_message

4. Pour broadcaster un événement personnalisé:
   from headphones.websocket import WebSocketManager
   WebSocketManager.broadcast('custom_event', {'data': 'value'})

5. Vérifier si des clients sont connectés:
   from headphones.websocket import WebSocketManager
   if len(WebSocketManager.clients) > 0:
       # Des clients sont connectés
       pass
"""
