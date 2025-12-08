#!/bin/bash

# Script pour arrêter Headphones

echo "Arrêt de Headphones..."
pkill -f Headphones.py

if [ $? -eq 0 ]; then
    echo "Headphones arrêté avec succès."
else
    echo "Aucun processus Headphones trouvé."
fi