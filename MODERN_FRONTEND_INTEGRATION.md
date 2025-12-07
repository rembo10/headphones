# Headphones Modern Frontend Integration

Ce document explique comment le nouveau frontend React moderne est intégré avec le backend Python de Headphones.

## Architecture

L'architecture se compose de trois parties principales :

### 1. API REST v2 (`headphones/api_v2.py`)

Une nouvelle API REST moderne avec des endpoints pour :

- **Artistes** : `/api/v2/artists`
  - GET - Liste tous les artistes
  - GET avec `?id=xxx` - Détails d'un artiste
  - POST - Ajouter un artiste
  - PUT avec `?id=xxx` - Modifier un artiste
  - DELETE avec `?id=xxx` - Supprimer un artiste

- **Albums** : `/api/v2/albums`
  - GET - Liste tous les albums
  - GET avec `?id=xxx` - Détails d'un album
  - GET avec `?artist_id=xxx` - Albums d'un artiste

- **Pistes** : `/api/v2/tracks`
  - GET avec `?album_id=xxx` - Pistes d'un album

- **Recherche** : `/api/v2/search`
  - GET avec `?query=xxx&type=artist` - Recherche d'artistes

- **Artwork** : `/api/v2/artwork/{type}/{id}`
  - GET - Images des artistes et albums

- **Statistiques** : `/api/v2/stats`
  - GET - Statistiques de la bibliothèque

### 2. WebSocket Server (`headphones/websocket.py`)

Serveur WebSocket pour les notifications en temps réel :

- **Événements supportés** :
  - `download_started` - Téléchargement démarré
  - `download_completed` - Téléchargement terminé
  - `artist_added` - Artiste ajouté
  - `album_wanted` - Album marqué comme recherché
  - `search_started` - Recherche démarrée
  - `search_completed` - Recherche terminée
  - `error` - Erreur
  - `info` - Information

**Utilisation dans le code** :
```python
from headphones.websocket import notify_websocket

# Envoyer une notification
notify_websocket('download_started', artist='Artist Name', album='Album Title')
```

### 3. Frontend React (`frontend/`)

Interface moderne construite avec :
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS
- Zustand (gestion d'état)
- React Router
- WebSocket client intégré

## Installation

### 1. Installer les dépendances WebSocket

```bash
pip install -r requirements-websocket.txt
```

Ou manuellement :
```bash
pip install ws4py
```

### 2. Construire le frontend

```bash
cd frontend
npm install
npm run build
```

Le frontend sera compilé dans `data/interfaces/modern/`

### 3. Démarrer Headphones

```bash
python Headphones.py
```

## Accès

- **Frontend classique** : `http://localhost:8181/`
- **Frontend moderne** : `http://localhost:8181/modern/`
- **API v2** : `http://localhost:8181/api/v2/`
- **WebSocket** : `ws://localhost:8181/ws`

## Configuration dans webstart.py

Le fichier `headphones/webstart.py` a été modifié pour :

1. **Monter l'API v2** :
   ```python
   cherrypy.tree.mount(APIV2(), '/api/v2', config={...})
   ```

2. **Servir le frontend React** :
   ```python
   conf['/modern'] = {
       'tools.staticdir.on': True,
       'tools.staticdir.dir': modern_interface_path,
       'tools.staticdir.index': 'index.html'
   }
   ```

3. **Configurer le WebSocket** :
   ```python
   setup_websocket(cherrypy)
   conf['/ws'] = {
       'tools.websocket.on': True,
       'tools.websocket.handler_cls': WebSocketHandler
   }
   ```

## Intégration des notifications WebSocket

Pour envoyer des notifications depuis n'importe où dans le code :

```python
from headphones.websocket import notify_websocket

# Téléchargement démarré
notify_websocket('download_started', 
                 artist='Pink Floyd', 
                 album='The Dark Side of the Moon')

# Artiste ajouté
notify_websocket('artist_added', 
                 artist='The Beatles', 
                 artist_id='b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d')

# Erreur
notify_websocket('error', error_message='Failed to download album')
```

### Exemple d'intégration dans searcher.py

```python
# Dans la fonction de téléchargement
from headphones.websocket import notify_websocket

def download_album(album_id):
    # ... code existant ...
    
    # Notifier le début du téléchargement
    notify_websocket('download_started', 
                     artist=album['ArtistName'], 
                     album=album['AlbumTitle'])
    
    try:
        # ... logique de téléchargement ...
        
        # Notifier la fin du téléchargement
        notify_websocket('download_completed',
                         artist=album['ArtistName'],
                         album=album['AlbumTitle'])
    except Exception as e:
        # Notifier l'erreur
        notify_websocket('error', error_message=str(e))
```

## Développement du frontend

### Mode développement

```bash
cd frontend
npm run dev
```

Le serveur de développement Vite :
- Démarre sur `http://localhost:3000`
- Proxy les requêtes API vers `http://localhost:8181`
- Hot Module Replacement (HMR)

### Structure du frontend

```
frontend/
├── src/
│   ├── components/       # Composants réutilisables
│   ├── pages/           # Pages de l'application
│   ├── services/        # Services API et WebSocket
│   │   ├── api.ts       # Client API REST
│   │   ├── music.ts     # Services musique
│   │   └── websocket.ts # Client WebSocket
│   ├── store/           # Gestion d'état Zustand
│   ├── hooks/           # Custom React hooks
│   ├── types/           # Types TypeScript
│   └── utils/           # Utilitaires
├── public/              # Fichiers statiques
└── package.json
```

## Tests

### Tester l'API

```bash
# Liste des artistes
curl http://localhost:8181/api/v2/artists

# Détails d'un artiste
curl http://localhost:8181/api/v2/artists?id=ARTIST_ID

# Ajouter un artiste
curl -X POST http://localhost:8181/api/v2/artists \
  -H "Content-Type: application/json" \
  -d '{"name": "The Beatles"}'

# Statistiques
curl http://localhost:8181/api/v2/stats
```

### Tester le WebSocket

Depuis la console du navigateur sur `http://localhost:8181/modern/` :

```javascript
// Connexion WebSocket
const ws = new WebSocket('ws://localhost:8181/ws');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => console.log('Message:', JSON.parse(event.data));
ws.onerror = (error) => console.error('Error:', error);

// Envoyer un ping
ws.send(JSON.stringify({ type: 'ping' }));
```

## Prochaines étapes

1. **Intégrer les notifications WebSocket dans tout le code** :
   - `searcher.py` - Notifications de téléchargement
   - `importer.py` - Notifications d'ajout d'artiste
   - `postprocessor.py` - Notifications de post-traitement

2. **Ajouter l'authentification** :
   - JWT tokens pour l'API
   - Session management
   - Middleware de sécurité

3. **Améliorer l'API** :
   - Pagination
   - Filtres avancés
   - Recherche full-text

4. **Tests** :
   - Tests unitaires pour l'API
   - Tests d'intégration
   - Tests E2E pour le frontend

## Dépannage

### WebSocket ne fonctionne pas

1. Vérifier que `ws4py` est installé :
   ```bash
   pip install ws4py
   ```

2. Vérifier les logs :
   ```bash
   tail -f logs/headphones.log
   ```

3. Tester la connexion :
   ```bash
   wscat -c ws://localhost:8181/ws
   ```

### Frontend ne se charge pas

1. Vérifier que le build existe :
   ```bash
   ls -la data/interfaces/modern/
   ```

2. Rebuilder le frontend :
   ```bash
   cd frontend
   npm run build
   ```

3. Vérifier les logs de CherryPy

### API retourne 404

1. Vérifier que l'API v2 est montée :
   - Regarder les logs au démarrage
   - Devrait afficher "Starting Headphones web server..."

2. Tester l'endpoint racine :
   ```bash
   curl http://localhost:8181/api/v2/
   ```

## Support

Pour toute question ou problème :
- Consulter les logs : `logs/headphones.log`
- Vérifier la configuration : `config.ini`
- Ouvrir une issue sur GitHub
