# 🎉 Nouveau: Interface React Moderne

Headphones dispose maintenant d'une interface utilisateur moderne construite avec React !

## ✨ Nouvelles Fonctionnalités

### Interface Moderne
- **React 18 + TypeScript** - Interface rapide et réactive
- **Design Responsive** - Fonctionne sur desktop, tablette et mobile
- **Thème Clair/Sombre** - Changez de thème selon vos préférences
- **Navigation Fluide** - React Router pour une expérience sans rechargement

### Notifications Temps Réel
- **WebSocket** - Notifications instantanées
- **Événements en Direct** - Suivez vos téléchargements en temps réel
- **Alertes** - Restez informé des événements importants

### API REST v2
- **Endpoints Modernes** - API RESTful complète
- **Format JSON** - Facile à intégrer
- **CORS** - Accès depuis n'importe quelle origine
- **Documentation** - Endpoints bien documentés

## 🚀 Installation Rapide

### 1. Prérequis
- Node.js 18+ ([télécharger](https://nodejs.org/))
- Python 3.7+ avec pip

### 2. Installation Automatique

```bash
# Exécuter le script de configuration
./setup-modern-frontend.sh
```

### 3. Installation Manuelle

```bash
# Installer les dépendances WebSocket
pip install ws4py

# Construire le frontend
cd frontend
npm install
npm run build
cd ..
```

### 4. Démarrer Headphones

```bash
python Headphones.py
```

## 🌐 Accès

- **Interface Classique**: http://localhost:8181/
- **Interface Moderne**: http://localhost:8181/modern/
- **API v2**: http://localhost:8181/api/v2/
- **WebSocket**: ws://localhost:8181/ws

## 📚 Documentation

### Guide Complet
Consultez [MODERN_FRONTEND_INTEGRATION.md](MODERN_FRONTEND_INTEGRATION.md) pour:
- Architecture détaillée
- Documentation de l'API
- Guide d'intégration WebSocket
- Exemples de code
- Dépannage

### Développement Frontend

```bash
cd frontend
npm run dev
# Serveur de développement: http://localhost:3000
```

## 🎨 Captures d'écran

### Page d'accueil moderne
![Modern Home](docs/screenshots/modern-home.png)

### Liste des artistes
![Artists Page](docs/screenshots/modern-artists.png)

### Thème sombre
![Dark Theme](docs/screenshots/modern-dark.png)

## 🔌 API v2 Endpoints

### Artistes
```bash
GET    /api/v2/artists          # Liste tous les artistes
GET    /api/v2/artists?id=xxx   # Détails d'un artiste
POST   /api/v2/artists          # Ajouter un artiste
PUT    /api/v2/artists?id=xxx   # Modifier un artiste
DELETE /api/v2/artists?id=xxx   # Supprimer un artiste
```

### Albums
```bash
GET /api/v2/albums                  # Liste tous les albums
GET /api/v2/albums?id=xxx           # Détails d'un album
GET /api/v2/albums?artist_id=xxx    # Albums d'un artiste
```

### Autres
```bash
GET /api/v2/tracks?album_id=xxx     # Pistes d'un album
GET /api/v2/search?query=xxx        # Recherche
GET /api/v2/stats                   # Statistiques
GET /api/v2/artwork/{type}/{id}     # Images
```

## 📡 WebSocket Events

Le serveur WebSocket envoie des notifications en temps réel:

- `download_started` - Téléchargement démarré
- `download_completed` - Téléchargement terminé
- `artist_added` - Artiste ajouté
- `album_wanted` - Album marqué comme recherché
- `search_started` - Recherche démarrée
- `search_completed` - Recherche terminée
- `error` - Erreur
- `info` - Information

### Exemple de connexion

```javascript
const ws = new WebSocket('ws://localhost:8181/ws');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Event:', message.type, message.data);
};
```

## 🛠️ Développement

### Structure du projet

```
headphones/
├── headphones/
│   ├── api_v2.py                      # API REST v2
│   ├── websocket.py                   # Serveur WebSocket
│   ├── websocket_plugin.py            # Plugin CherryPy
│   └── websocket_integration_examples.py
├── frontend/                           # Frontend React
│   ├── src/
│   │   ├── components/                # Composants UI
│   │   ├── pages/                     # Pages
│   │   ├── services/                  # API & WebSocket
│   │   └── store/                     # État global
│   └── package.json
└── data/interfaces/modern/             # Frontend compilé
```

### Contribuer

1. **Fork** le projet
2. **Créer** une branche feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add some AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. **Ouvrir** une Pull Request

### Tests

```bash
# Backend (API)
python -m pytest tests/

# Frontend
cd frontend
npm test
```

## 🐛 Dépannage

### Le WebSocket ne fonctionne pas

```bash
# Vérifier que ws4py est installé
pip install ws4py

# Vérifier les logs
tail -f logs/headphones.log
```

### Le frontend ne se charge pas

```bash
# Rebuilder le frontend
cd frontend
npm run build

# Vérifier que le dossier existe
ls -la data/interfaces/modern/
```

### API retourne 404

```bash
# Tester l'endpoint racine
curl http://localhost:8181/api/v2/

# Devrait retourner:
# {"message": "Headphones API v2", "version": "2.0"}
```

## 📖 Plus d'informations

- [Guide d'utilisation original](../../wiki/Usage-guide)
- [Documentation API v2](MODERN_FRONTEND_INTEGRATION.md)
- [Exemples d'intégration WebSocket](headphones/websocket_integration_examples.py)

## 💬 Support

- IRC: `#headphones` sur Freenode
- Issues GitHub: [github.com/rembo10/headphones/issues](https://github.com/rembo10/headphones/issues)

## 📄 License

GPL v3 - Voir [LICENSE](LICENSE)

---

**Note**: L'interface classique reste disponible et entièrement fonctionnelle. Le nouveau frontend React est une amélioration optionnelle qui coexiste avec l'interface originale.
