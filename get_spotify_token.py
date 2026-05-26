#!/usr/bin/env python3
"""
One-time helper to get your Spotify refresh token.

Run this script ONCE locally:
    python3 get_spotify_token.py

It will:
  1. Ask for your Spotify Client ID and Client Secret
  2. Open your browser to the Spotify auth page
  3. Catch the callback on localhost:8888
  4. Exchange the code for tokens
  5. Print the 3 values you need to add as GitHub Secrets

Prerequisites:
  - A Spotify Developer App at https://developer.spotify.com/dashboard
  - Add  http://localhost:8888/callback  as a Redirect URI in the app settings
"""

import base64
import json
import ssl
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

CLIENT_ID     = input("Spotify Client ID     : ").strip()
CLIENT_SECRET = input("Spotify Client Secret : ").strip()
REDIRECT_URI  = "http://127.0.0.1:8888/callback"
SCOPE         = "user-read-currently-playing user-read-recently-played"

# ── Step 1: open auth URL in browser ───────────────────────────────────────────
params = urllib.parse.urlencode({
    "client_id":     CLIENT_ID,
    "response_type": "code",
    "redirect_uri":  REDIRECT_URI,
    "scope":         SCOPE,
})
auth_url = f"https://accounts.spotify.com/authorize?{params}"
print(f"\nOpening browser for Spotify login...\nIf it doesn't open, visit:\n{auth_url}\n")
webbrowser.open(auth_url)


# ── Step 2: catch the callback ──────────────────────────────────────────────────
auth_code = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        qs     = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            auth_code = qs["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Got it! You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>No code found. Try again.</h2>")

    def log_message(self, *args):
        pass   # silence request logs

server = HTTPServer(("localhost", 8888), Handler)
print("Waiting for Spotify callback on http://localhost:8888 ...")
server.handle_request()   # handles exactly one request then returns

if not auth_code:
    print("ERROR: No authorization code received. Exiting.")
    raise SystemExit(1)


# ── Step 3: exchange code for tokens ───────────────────────────────────────────
credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
data = urllib.parse.urlencode({
    "grant_type":   "authorization_code",
    "code":         auth_code,
    "redirect_uri": REDIRECT_URI,
}).encode()

req = urllib.request.Request(
    "https://accounts.spotify.com/api/token",
    data=data,
    headers={
        "Authorization": f"Basic {credentials}",
        "Content-Type":  "application/x-www-form-urlencoded",
    },
    method="POST",
)

try:
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        tokens = json.loads(r.read())
except Exception:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        tokens = json.loads(r.read())

refresh_token = tokens.get("refresh_token", "")
if not refresh_token:
    print("ERROR: No refresh token in response:", tokens)
    raise SystemExit(1)


# ── Step 4: print the values ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUCCESS! Add these 3 secrets to your GitHub repo:")
print("  Settings -> Secrets and variables -> Actions -> New secret")
print("=" * 60)
print(f"\n  SPOTIFY_CLIENT_ID     =  {CLIENT_ID}")
print(f"  SPOTIFY_CLIENT_SECRET =  {CLIENT_SECRET}")
print(f"  SPOTIFY_REFRESH_TOKEN =  {refresh_token}")
print("\n" + "=" * 60)
print("Done! You can close this window.")
