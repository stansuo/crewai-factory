"""Spike: verify posting via POST /2/tweets (OAuth 1.0a user context).

Credentials are read from environment variables (or a local .env file).
Never hardcode keys in this file. Required variables — see .env.example:
    X_CONSUMER_KEY, X_CONSUMER_KEY_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET

WARNING: running this script publishes a real post to the authenticated
account (~0.02 USD/post). Delete the test post afterwards if unwanted.
"""

import os
import sys

import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

load_dotenv()  # picks up .env from the project root, if present

REQUIRED_VARS = [
    "X_CONSUMER_KEY",
    "X_CONSUMER_KEY_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
]

missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
if missing:
    print(f"Missing environment variables: {', '.join(missing)}")
    print("Set them in your local .env (see .env.example). Never commit real keys.")
    sys.exit(1)

auth = OAuth1(
    os.getenv("X_CONSUMER_KEY"),
    os.getenv("X_CONSUMER_KEY_SECRET"),
    os.getenv("X_ACCESS_TOKEN"),
    os.getenv("X_ACCESS_TOKEN_SECRET"),
)

url = "https://api.x.com/2/tweets"

payload = {
    "text": "Test post from Python + X API v2 (safe to delete)"
}

response = requests.post(url, auth=auth, json=payload)

print("Status code:", response.status_code)
print("Response body:")
print(response.json())
