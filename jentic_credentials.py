#!/usr/bin/env python3
"""
Jentic One credential management helper for InferenceIndexer.
Stores and retrieves API keys for AI inference providers.

Usage:
  python3 jentic_credentials.py store <provider> <api_key>
  python3 jentic_credentials.py get <provider>
  python3 jentic_credentials.py list
  python3 jentic_credentials.py login
"""
import sys
import json
import requests

JENTIC_URL = "http://127.0.0.1:8001"
JENTIC_EMAIL = "frank@desmartin.io"
JENTIC_PASSWORD = "JenticOne2026!"

# Token cache file
TOKEN_FILE = "/tmp/.jentic_token"

# Provider configs: (vendor, api_name, version, field_name, location)
PROVIDER_CONFIG = {
    "together": ("together.ai", "together", "v1", "Authorization", "header"),
    "groq": ("groq.com", "groq", "v1", "Authorization", "header"),
    "fireworks": ("fireworks.ai", "fireworks", "v1", "Authorization", "header"),
    "cerebras": ("cerebras.ai", "cerebras", "v1", "Authorization", "header"),
    "mistral": ("mistral.ai", "mistral", "v1", "Authorization", "header"),
    "siliconflow": ("siliconflow.cn", "siliconflow", "v1", "Authorization", "header"),
    "perplexity": ("perplexity.ai", "perplexity", "v1", "Authorization", "header"),
    "openai": ("openai.com", "openai", "v1", "Authorization", "header"),
    "anthropic": ("anthropic.com", "anthropic", "v1", "x-api-key", "header"),
    "hyperbolic": ("hyperbolic.xyz", "hyperbolic", "v1", "Authorization", "header"),
    "deepseek": ("deepseek.com", "deepseek", "v1", "Authorization", "header"),
    "moonshot": ("moonshot.cn", "moonshot", "v1", "Authorization", "header"),
    "tensorx": ("tensorx.ai", "tensorx", "v1", "Authorization", "header"),
}


def login():
    """Login to Jentic One and cache the token."""
    resp = requests.post(
        f"{JENTIC_URL}/auth/login",
        json={"email": JENTIC_EMAIL, "password": JENTIC_PASSWORD},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        return None
    token = resp.json().get("access_token")
    if token:
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        return token
    return None


def get_token():
    """Get cached token or login."""
    try:
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return login()


def store(provider_name, api_key):
    """Store an API key for a provider in Jentic One."""
    config = PROVIDER_CONFIG.get(provider_name.lower())
    if not config:
        print(f"Unknown provider: {provider_name}")
        print(f"Available: {', '.join(PROVIDER_CONFIG.keys())}")
        return False

    vendor, api_name, version, field_name, location = config
    token = get_token()
    if not token:
        print("Cannot authenticate with Jentic One")
        return False

    payload = {
        "type": "api_key",
        "name": f"{provider_name.title()} API Key",
        "api": {
            "vendor": vendor,
            "name": api_name,
            "version": version,
        },
        "provider": "static",
        "key": api_key,
        "location": location,
        "field_name": field_name,
    }

    resp = requests.post(
        f"{JENTIC_URL}/credentials",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if resp.status_code in (200, 201):
        data = resp.json()
        cred_id = data.get("id", "?")
        print(f"Stored credential for {provider_name} (id: {cred_id})")
        return True
    else:
        print(f"Failed to store: {resp.status_code} {resp.text[:200]}")
        return False


def get_credential(provider_name):
    """Retrieve an API key for a provider from Jentic One."""
    config = PROVIDER_CONFIG.get(provider_name.lower())
    if not config:
        print(f"Unknown provider: {provider_name}")
        return None

    vendor, api_name, version, _, _ = config
    token = get_token()
    if not token:
        print("Cannot authenticate with Jentic One")
        return None

    # List all credentials and find the one for this provider
    resp = requests.get(
        f"{JENTIC_URL}/credentials",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"Failed to list credentials: {resp.status_code}")
        return None

    creds = resp.json().get("data", [])
    for cred in creds:
        api = cred.get("api", {})
        if api.get("vendor") == vendor or provider_name.lower() in cred.get("name", "").lower():
            # The key is not returned after create for security
            # We need to use the credential via the broker, not retrieve it directly
            print(f"Found credential: {cred.get('name')} (id: {cred.get('id')})")
            print(f"  API: {api.get('vendor')}/{api.get('name')}/{api.get('version')}")
            print(f"  NOTE: Key is encrypted and not retrievable via API.")
            print(f"  Use the Jentic broker to make authenticated requests.")
            return cred.get("id")

    print(f"No credential found for {provider_name}")
    return None


def list_credentials():
    """List all stored credentials."""
    token = get_token()
    if not token:
        print("Cannot authenticate with Jentic One")
        return

    resp = requests.get(
        f"{JENTIC_URL}/credentials",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"Failed: {resp.status_code}")
        return

    creds = resp.json().get("data", [])
    if not creds:
        print("No credentials stored.")
        return

    print(f"Stored credentials ({len(creds)}):")
    for cred in creds:
        api = cred.get("api", {})
        print(f"  {cred.get('name', '?'):30s} | {api.get('vendor', '?')}/{api.get('name', '?')} | id: {cred.get('id', '?')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "login":
        token = login()
        if token:
            print(f"Logged in. Token cached.")
        else:
            print("Login failed.")
    elif cmd == "store":
        if len(sys.argv) < 4:
            print("Usage: store <provider> <api_key>")
            sys.exit(1)
        store(sys.argv[2], sys.argv[3])
    elif cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: get <provider>")
            sys.exit(1)
        get_credential(sys.argv[2])
    elif cmd == "list":
        list_credentials()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
