#!/bin/bash

# Script de test pour vérifier l'intégration backend/frontend

echo "=========================================="
echo "Tests d'Intégration Backend/Frontend"
echo "=========================================="
echo ""

HEADPHONES_URL="http://localhost:8181"
API_URL="$HEADPHONES_URL/api/v2"

# Fonction pour tester une URL
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    echo -n "Testing $name... "
    
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response_code" = "$expected_code" ]; then
        echo "✓ OK ($response_code)"
        return 0
    else
        echo "✗ FAIL (got $response_code, expected $expected_code)"
        return 1
    fi
}

# Vérifier que Headphones est démarré
echo "1. Vérification du serveur Headphones..."
if ! curl -s "$HEADPHONES_URL" > /dev/null 2>&1; then
    echo "❌ Headphones ne semble pas être démarré sur $HEADPHONES_URL"
    echo "   Démarrez-le avec: python Headphones.py"
    exit 1
fi
echo "✓ Serveur Headphones actif"
echo ""

# Tester l'interface classique
echo "2. Test de l'interface classique..."
test_endpoint "Interface classique" "$HEADPHONES_URL/" 200
echo ""

# Tester l'API v2
echo "3. Test de l'API v2..."
test_endpoint "API v2 root" "$API_URL/" 200
test_endpoint "API v2 artists" "$API_URL/artists" 200
test_endpoint "API v2 albums" "$API_URL/albums" 200
test_endpoint "API v2 stats" "$API_URL/stats" 200
echo ""

# Tester le frontend moderne
echo "4. Test du frontend moderne..."
modern_path="$HEADPHONES_URL/modern/"
if curl -s "$modern_path" > /dev/null 2>&1; then
    test_endpoint "Frontend moderne" "$modern_path" 200
else
    echo "⚠️  Frontend moderne non accessible"
    echo "   Le frontend n'est peut-être pas encore construit."
    echo "   Exécutez: ./setup-modern-frontend.sh"
fi
echo ""

# Test détaillé de l'API
echo "5. Tests détaillés de l'API..."

# Test de l'API root
echo -n "Testing API response format... "
api_response=$(curl -s "$API_URL/")
if echo "$api_response" | grep -q "Headphones API v2"; then
    echo "✓ OK"
else
    echo "✗ FAIL"
    echo "Response: $api_response"
fi

# Test des artistes
echo -n "Testing artists endpoint... "
artists_response=$(curl -s "$API_URL/artists")
if echo "$artists_response" | grep -q "\["; then
    echo "✓ OK (valid JSON array)"
else
    echo "✗ FAIL"
    echo "Response: $artists_response"
fi

# Test des stats
echo -n "Testing stats endpoint... "
stats_response=$(curl -s "$API_URL/stats")
if echo "$stats_response" | grep -q "artists"; then
    echo "✓ OK"
    echo "   Stats: $stats_response"
else
    echo "✗ FAIL"
    echo "Response: $stats_response"
fi
echo ""

# Vérifier les fichiers critiques
echo "6. Vérification des fichiers..."

files_to_check=(
    "headphones/api_v2.py:API v2"
    "headphones/websocket.py:WebSocket server"
    "headphones/websocket_plugin.py:WebSocket plugin"
)

all_files_ok=true
for item in "${files_to_check[@]}"; do
    IFS=':' read -r file desc <<< "$item"
    echo -n "Checking $desc... "
    if [ -f "$file" ]; then
        echo "✓ OK"
    else
        echo "✗ MISSING"
        all_files_ok=false
    fi
done
echo ""

# Vérifier le frontend build
echo "7. Vérification du build frontend..."
modern_dir="data/interfaces/modern"
echo -n "Checking modern frontend directory... "
if [ -d "$modern_dir" ]; then
    echo "✓ OK"
    
    # Vérifier les fichiers essentiels
    echo -n "Checking index.html... "
    if [ -f "$modern_dir/index.html" ]; then
        echo "✓ OK"
    else
        echo "✗ MISSING"
        echo "   Exécutez: cd frontend && npm run build"
    fi
else
    echo "✗ MISSING"
    echo "   Le frontend n'a pas été construit."
    echo "   Exécutez: ./setup-modern-frontend.sh"
fi
echo ""

# Test WebSocket (si wscat est installé)
echo "8. Test WebSocket..."
if command -v wscat &> /dev/null; then
    echo "Testing WebSocket connection..."
    timeout 2 wscat -c "ws://localhost:8181/ws" > /dev/null 2>&1
    if [ $? -eq 124 ]; then
        echo "✓ WebSocket est accessible (timeout après connexion)"
    else
        echo "⚠️  WebSocket peut ne pas être configuré"
        echo "   Vérifiez que ws4py est installé: pip install ws4py"
    fi
else
    echo "⚠️  wscat non installé, impossible de tester WebSocket"
    echo "   Pour tester manuellement, installez wscat:"
    echo "   npm install -g wscat"
    echo "   Puis: wscat -c ws://localhost:8181/ws"
fi
echo ""

# Résumé
echo "=========================================="
echo "Résumé des tests"
echo "=========================================="
echo ""

if [ "$all_files_ok" = true ]; then
    echo "✅ Tous les fichiers backend sont présents"
else
    echo "⚠️  Certains fichiers backend sont manquants"
fi

echo ""
echo "Pour accéder à l'application:"
echo "  - Interface classique: $HEADPHONES_URL/"
echo "  - Interface moderne:   $HEADPHONES_URL/modern/"
echo "  - API v2:             $API_URL/"
echo ""

echo "Pour voir les logs en temps réel:"
echo "  tail -f logs/headphones.log"
echo ""

echo "Pour développer le frontend:"
echo "  cd frontend"
echo "  npm run dev"
echo "  # Serveur de dev: http://localhost:3000"
echo ""
