#!/bin/bash

# Script de configuration rapide pour le frontend React moderne de Headphones

echo "=========================================="
echo "Configuration du Frontend React Moderne"
echo "=========================================="
echo ""

# Vérifier si Node.js est installé
if ! command -v node &> /dev/null; then
    echo "❌ Node.js n'est pas installé."
    echo "   Installez Node.js 18+ depuis https://nodejs.org/"
    exit 1
fi

echo "✓ Node.js $(node --version) détecté"

# Vérifier si npm est installé
if ! command -v npm &> /dev/null; then
    echo "❌ npm n'est pas installé."
    exit 1
fi

echo "✓ npm $(npm --version) détecté"
echo ""

# Vérifier python3
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 n'est pas installé."
    echo "   Installez python3 (ou python-is-python3) puis relancez le script."
    exit 1
fi

PYTHON_BIN="$(command -v python3)"
VENV_DIR=".venv"

# Installer les dépendances WebSocket Python
echo "📦 Installation des dépendances WebSocket..."
if [ ! -d "$VENV_DIR" ]; then
    echo "  Création d'un environnement virtuel ($VENV_DIR)..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "❌ Échec de la création de l'environnement virtuel"
    exit 1
fi

source "$VENV_DIR/bin/activate"

pip install --upgrade pip >/dev/null 2>&1
if pip install -r requirements-websocket.txt >/dev/null 2>&1; then
    echo "✓ Dépendances WebSocket installées dans $VENV_DIR"
elif pip install ws4py >/dev/null 2>&1; then
    echo "✓ ws4py installé dans $VENV_DIR"
else
    echo "⚠️  Erreur lors de l'installation des dépendances WebSocket"
    echo "   Continuez quand même..."
fi

echo ""

# Aller dans le dossier frontend
cd frontend

# Installer les dépendances npm
echo "📦 Installation des dépendances npm..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de l'installation des dépendances npm"
    exit 1
fi

echo "✓ Dépendances npm installées"
echo ""

# Construire le frontend
echo "🔨 Construction du frontend..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la construction du frontend"
    exit 1
fi

echo "✓ Frontend construit avec succès"
echo ""

# Vérifier que le dossier de build existe
if [ -d "../data/interfaces/modern" ]; then
    echo "✓ Frontend déployé dans data/interfaces/modern/"
else
    echo "❌ Le dossier de build n'a pas été créé"
    exit 1
fi

cd ..

echo ""
echo "=========================================="
echo "✅ Configuration terminée avec succès!"
echo "=========================================="
echo ""
echo "Pour démarrer Headphones:"
echo "  source .venv/bin/activate"
echo "  python3 Headphones.py"
echo ""
echo "Accès au frontend:"
echo "  - Interface classique: http://localhost:8181/"
echo "  - Interface moderne:   http://localhost:8181/modern/"
echo "  - API v2:             http://localhost:8181/api/v2/"
echo "  - WebSocket:          ws://localhost:8181/ws"
echo ""
echo "Pour le développement du frontend:"
echo "  cd frontend"
echo "  npm run dev"
echo "  # Le serveur de dev sera sur http://localhost:3000"
echo ""
