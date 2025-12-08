#!/bin/bash

# Script pour démarrer Headphones
# Assurez-vous d'être dans le répertoire de Headphones

cd /opt/headphones

# Vérifier si l'environnement virtuel existe
if [ ! -d ".venv" ]; then
    echo "L'environnement virtuel .venv n'existe pas. Lancez d'abord ./setup-modern-frontend.sh"
    exit 1
fi

# Activer l'environnement virtuel
source .venv/bin/activate

# Vérifier si Python 3 est disponible dans l'environnement virtuel
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON_CMD="python"
else
    echo "Python 3 n'est pas disponible dans l'environnement virtuel."
    exit 1
fi

# Lancer Headphones en arrière-plan avec verbose pour le debug
echo "Démarrage de Headphones en arrière-plan (mode verbose)..."
nohup $PYTHON_CMD Headphones.py --verbose > headphones.log 2>&1 &

# Attendre un peu que le serveur démarre
sleep 5

# Vérifier si le processus est en cours
if pgrep -f "Headphones.py" > /dev/null; then
    echo "Headphones démarré avec succès. Accessible sur http://localhost:8181"
    echo "Pour arrêter : pkill -f Headphones.py"
else
    echo "Échec du démarrage de Headphones. Vérifiez headphones.log"
fi