#!/usr/bin/env python3
"""
Script de test pour simuler la sauvegarde des paramètres avancés
"""
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, '/opt/headphones')

from headphones import config

# Initialiser la config
CONFIG = config.Config('/opt/headphones/config.ini')
CONFIG.read()

print("\n=== Test de sauvegarde des paramètres avancés ===\n")

# Simuler des paramètres comme ceux envoyés depuis l'onglet Advanced Settings
test_kwargs = {
    'customauth': '1',
    'autowant_all': '1',
    'autowant_upcoming': '0',
    'include_extras': '1',
    'official_releases_only': '0',
    'wait_until_release_date': '1',
    'freeze_db': '0',
    'idtag': '1',
}

print(f"Paramètres de test : {test_kwargs}\n")

try:
    print("Appel de process_kwargs...")
    CONFIG.process_kwargs(test_kwargs)
    print("✓ process_kwargs a réussi\n")
    
    print("Écriture de la configuration...")
    CONFIG.write()
    print("✓ Configuration écrite avec succès\n")
    
    print("=== Test réussi ! ===")
    
except Exception as e:
    print(f"✗ Erreur : {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
