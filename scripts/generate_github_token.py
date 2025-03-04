#!/usr/bin/env python3
import jwt
import time
import requests
import sys
from pathlib import Path

# App configuration
APP_ID = "1165094"
INSTALLATION_ID = "62021279"
PRIVATE_KEY_PATH = "cahoots-package-reader.2025-03-03.private-key.pem"

def generate_jwt():
    """Generate a JWT for GitHub App authentication."""
    with open(PRIVATE_KEY_PATH, 'rb') as key_file:
        private_key = key_file.read()
    
    now = int(time.time())
    payload = {
        'iat': now,
        'exp': now + (10 * 60),  # Token expires in 10 minutes
        'iss': APP_ID
    }
    
    return jwt.encode(payload, private_key, algorithm='RS256')

def get_installation_token():
    """Get an installation access token."""
    jwt_token = generate_jwt()
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.post(
        f'https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens',
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"Error getting token: {response.status_code}")
        print(response.json())
        sys.exit(1)
    
    return response.json()['token']

if __name__ == '__main__':
    token = get_installation_token()
    print(token) 