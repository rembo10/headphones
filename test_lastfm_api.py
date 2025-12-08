#!/usr/bin/env python3
"""Test script for Last.fm API key validation"""

import requests
import json

def test_lastfm_api():
    api_key = '4cecf26d70998e5bb4238e37a1408db7'
    url = 'http://ws.audioscrobbler.com/2.0/'
    
    print("🔍 Testing Last.fm API Key...")
    print(f"API Key: {api_key}")
    print()
    
    # Test 1: Simple artist query
    print("Test 1: Artist Info Query")
    params = {
        'method': 'artist.getinfo',
        'artist': 'Cher',
        'api_key': api_key,
        'format': 'json'
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            if 'error' in data:
                print(f"❌ Last.fm API Error Code: {data.get('error')}")
                print(f"   Message: {data.get('message')}")
                print()
                print("Codes d'erreur courants:")
                print("  2 = Invalid service (clé invalide)")
                print("  10 = Invalid API key")
                print("  26 = Suspended API key")
            else:
                print("✅ Clé API VALIDE - Réponse OK")
                if 'artist' in data:
                    print(f"   Artist trouvé: {data['artist'].get('name')}")
        else:
            print(f"❌ Erreur HTTP: {r.status_code}")
            print(f"   Réponse: {r.text[:500]}")
    except requests.Timeout:
        print("⏱️  Timeout - Last.fm ne répond pas")
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")
    
    print()
    
    # Test 2: Album query (celui qui échoue dans vos logs)
    print("Test 2: Album Info Query")
    params = {
        'method': 'album.getinfo',
        'artist': 'Cher',
        'album': 'Believe',
        'api_key': api_key,
        'format': 'json'
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            if 'error' in data:
                print(f"❌ Last.fm API Error Code: {data.get('error')}")
                print(f"   Message: {data.get('message')}")
            else:
                print("✅ Album trouvé")
                if 'album' in data:
                    print(f"   Album: {data['album'].get('name')}")
        elif r.status_code == 404:
            print("⚠️  404 Not Found - Album non trouvé dans Last.fm")
            print("   (C'est normal pour certains albums)")
        else:
            print(f"❌ Erreur HTTP: {r.status_code}")
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    test_lastfm_api()
