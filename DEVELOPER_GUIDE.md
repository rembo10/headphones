# 🛠️ Guide du Développeur - Frontend React Moderne

## 🎯 Vue d'ensemble

Ce guide s'adresse aux développeurs qui souhaitent contribuer ou modifier le frontend React moderne de Headphones.

## 🏗️ Architecture Technique

### Backend (Python)

```
headphones/
├── api_v2.py                    # API REST v2
│   ├── APIV2                   # Classe principale
│   ├── artists()               # CRUD artistes
│   ├── albums()                # Lecture albums
│   ├── tracks()                # Lecture pistes
│   ├── search()                # Recherche
│   ├── artwork()               # Images
│   └── stats()                 # Statistiques
│
├── websocket.py                 # Serveur WebSocket
│   ├── WebSocketHandler        # Gestion des connexions
│   ├── WebSocketManager        # Broadcast manager
│   └── notify_websocket()      # Helper function
│
├── websocket_plugin.py          # Plugin CherryPy
│   ├── setup_websocket()       # Configuration
│   └── create_websocket_config()
│
└── webstart.py                  # Configuration serveur
    ├── Mount API v2
    ├── Mount Frontend
    └── Setup WebSocket
```

### Frontend (React + TypeScript)

```
frontend/src/
├── components/                  # Composants réutilisables
│   ├── Header.tsx              # En-tête avec notifications
│   ├── Sidebar.tsx             # Menu de navigation
│   ├── Layout.tsx              # Layout principal
│   ├── ArtistCard.tsx          # Carte artiste
│   ├── AlbumCard.tsx           # Carte album
│   └── LoadingSpinner.tsx      # Indicateur de chargement
│
├── pages/                       # Pages de l'application
│   ├── HomePage.tsx            # Dashboard
│   ├── ArtistsPage.tsx         # Liste des artistes
│   ├── AlbumsPage.tsx          # Liste des albums
│   └── SettingsPage.tsx        # Paramètres
│
├── services/                    # Services externes
│   ├── api.ts                  # Client API REST
│   ├── music.ts                # Services musique
│   └── websocket.ts            # Client WebSocket
│
├── store/                       # Gestion d'état (Zustand)
│   ├── music.ts                # Store musique
│   └── theme.ts                # Store thème
│
├── hooks/                       # Custom React hooks
│   └── useWebSocket.ts         # Hook WebSocket
│
├── types/                       # Types TypeScript
│   └── index.ts                # Types principaux
│
├── utils/                       # Utilitaires
│   └── helpers.ts              # Fonctions helpers
│
├── styles/                      # Styles globaux
│   └── index.css               # CSS principal
│
└── main.tsx                     # Point d'entrée
```

## 🚀 Configuration de l'Environnement de Développement

### 1. Prérequis

- Node.js 18+
- npm 9+
- Python 3.7+
- pip

### 2. Installation

```bash
# Backend
pip install -r requirements-websocket.txt

# Frontend
cd frontend
npm install
```

### 3. Lancer en mode développement

#### Terminal 1: Backend
```bash
# Depuis la racine du projet
python Headphones.py
```

#### Terminal 2: Frontend
```bash
# Depuis le dossier frontend
cd frontend
npm run dev
```

Le frontend dev sera accessible sur http://localhost:3000 avec :
- Hot Module Replacement (HMR)
- Proxy vers l'API backend (port 8181)
- Source maps pour le debugging

## 📝 Conventions de Code

### Backend (Python)

```python
# PEP 8 style
# Utiliser des docstrings
def my_function(param1, param2):
    """
    Description de la fonction.
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Description du retour
    """
    pass

# Classes en PascalCase
class MyClass:
    pass

# Fonctions/variables en snake_case
def my_function():
    my_variable = "value"
```

### Frontend (TypeScript)

```typescript
// Utiliser TypeScript strict
// Composants en PascalCase
export function MyComponent({ prop1, prop2 }: Props) {
  // ...
}

// Hooks personnalisés avec préfixe "use"
export function useMyHook() {
  // ...
}

// Types/Interfaces en PascalCase
interface MyInterface {
  property: string;
}

// Constantes en UPPER_SNAKE_CASE
const API_BASE_URL = "/api/v2";
```

## 🔧 Ajouter une Nouvelle Fonctionnalité

### Ajouter un Endpoint API

1. **Modifier `api_v2.py`**

```python
@cherrypy.expose
@cherrypy.tools.json_out()
def my_new_endpoint(self, id=None, **kwargs):
    """
    GET /api/v2/my_new_endpoint - Description
    """
    method = cherrypy.request.method
    
    if method == "GET":
        return self._get_my_data(id)
    else:
        raise cherrypy.HTTPError(405, "Method not allowed")

def _get_my_data(self, id):
    """Get data from database"""
    try:
        data = self.db.select('SELECT * FROM my_table WHERE id=?', [id])
        return data
    except Exception as e:
        logger.error(f"Error: {e}")
        raise cherrypy.HTTPError(500, str(e))
```

2. **Ajouter le type TypeScript**

```typescript
// frontend/src/types/index.ts
export interface MyData {
  id: string;
  name: string;
  value: number;
}
```

3. **Créer le service**

```typescript
// frontend/src/services/mydata.ts
import { apiService } from './api';
import type { MyData } from '@/types';

export const myDataService = {
  getById: (id: string) => apiService.get<MyData>(`/my_new_endpoint?id=${id}`),
  getAll: () => apiService.get<MyData[]>('/my_new_endpoint'),
};
```

4. **Utiliser dans un composant**

```typescript
// frontend/src/pages/MyPage.tsx
import { useEffect, useState } from 'react';
import { myDataService } from '@/services/mydata';

export function MyPage() {
  const [data, setData] = useState<MyData[]>([]);
  
  useEffect(() => {
    myDataService.getAll().then(setData);
  }, []);
  
  return (
    <div>
      {data.map(item => (
        <div key={item.id}>{item.name}</div>
      ))}
    </div>
  );
}
```

### Ajouter une Notification WebSocket

1. **Ajouter la méthode dans `websocket.py`**

```python
@classmethod
def notify_my_event(cls, param1, param2):
    """Notify clients of my custom event"""
    cls.broadcast('my_event', {
        'param1': param1,
        'param2': param2,
        'message': f'My event: {param1} - {param2}'
    })
```

2. **Utiliser dans le code Python**

```python
from headphones.websocket import notify_websocket

notify_websocket('my_event', param1='value1', param2='value2')
```

3. **Écouter dans le frontend**

```typescript
// frontend/src/hooks/useMyEvent.ts
import { useWebSocket } from './useWebSocket';

export function useMyEvent() {
  const { data } = useWebSocket<MyEventData>('my_event');
  
  return data;
}
```

### Ajouter une Page

1. **Créer le composant de page**

```typescript
// frontend/src/pages/MyNewPage.tsx
export function MyNewPage() {
  return (
    <div>
      <h2>My New Page</h2>
      {/* Contenu */}
    </div>
  );
}
```

2. **Ajouter la route**

```typescript
// frontend/src/main.tsx
import { MyNewPage } from './pages/MyNewPage';

// Dans <Routes>
<Route path="/mynewpage" element={<MyNewPage />} />
```

3. **Ajouter au menu**

```typescript
// frontend/src/components/Sidebar.tsx
const navItems = [
  // ... items existants
  { to: '/mynewpage', icon: MyIcon, label: 'My New Page' },
];
```

## 🧪 Tests

### Tests Backend

```python
# tests/test_api_v2.py
import unittest
from headphones.api_v2 import APIV2

class TestAPIV2(unittest.TestCase):
    def setUp(self):
        self.api = APIV2()
    
    def test_get_artists(self):
        artists = self.api._get_all_artists()
        self.assertIsInstance(artists, list)
```

### Tests Frontend

```typescript
// frontend/src/components/__tests__/ArtistCard.test.tsx
import { render, screen } from '@testing-library/react';
import { ArtistCard } from '../ArtistCard';

describe('ArtistCard', () => {
  it('renders artist name', () => {
    const artist = {
      id: '1',
      name: 'Test Artist',
      status: 'active',
      albumCount: 5,
      trackCount: 50,
      dateAdded: '2023-01-01',
    };
    
    render(<ArtistCard artist={artist} />);
    expect(screen.getByText('Test Artist')).toBeInTheDocument();
  });
});
```

## 🔍 Debugging

### Backend

```python
# Ajouter des logs
from headphones import logger

logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning message')
logger.error('Error message')

# Voir les logs
tail -f logs/headphones.log
```

### Frontend

```typescript
// Console du navigateur
console.log('Debug:', data);

// React DevTools
// Installer l'extension React DevTools

// Network Tab
// F12 > Network pour voir les requêtes API
```

## 📦 Build et Déploiement

### Build de Production

```bash
cd frontend
npm run build
```

Le build sera dans `../data/interfaces/modern/`

### Optimisations

Le build Vite inclut :
- Minification du code
- Tree-shaking
- Code splitting
- Optimisation des assets

## 🎨 Personnalisation du Thème

### Modifier les couleurs

```javascript
// frontend/tailwind.config.js
theme: {
  extend: {
    colors: {
      primary: {
        50: '#f0f9ff',
        // ... autres nuances
        900: '#0c4a6e',
      },
    },
  },
}
```

### Ajouter des composants réutilisables

```typescript
// frontend/src/components/Button.tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
  onClick?: () => void;
}

export function Button({ variant = 'primary', children, onClick }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-4 py-2 rounded-md',
        variant === 'primary' && 'bg-primary text-white',
        variant === 'secondary' && 'bg-gray-200 text-gray-800'
      )}
    >
      {children}
    </button>
  );
}
```

## 🤝 Contribuer

### Workflow Git

```bash
# 1. Fork le projet
# 2. Créer une branche
git checkout -b feature/ma-nouvelle-fonctionnalite

# 3. Faire les modifications
# ... éditer les fichiers ...

# 4. Commit
git add .
git commit -m "feat: ajout de ma nouvelle fonctionnalité"

# 5. Push
git push origin feature/ma-nouvelle-fonctionnalite

# 6. Créer une Pull Request sur GitHub
```

### Convention de Commits

```
feat: Nouvelle fonctionnalité
fix: Correction de bug
docs: Documentation
style: Formatage
refactor: Refactorisation
test: Tests
chore: Maintenance
```

## 📚 Ressources

### Backend
- [CherryPy Documentation](https://docs.cherrypy.dev/)
- [ws4py Documentation](https://ws4py.readthedocs.io/)

### Frontend
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand](https://docs.pmnd.rs/zustand/)

## 🆘 Support

- GitHub Issues: [github.com/rembo10/headphones/issues](https://github.com/rembo10/headphones/issues)
- IRC: `#headphones` sur Freenode
- Documentation: [Wiki](../../wiki)

---

**Bon développement ! 🚀**
