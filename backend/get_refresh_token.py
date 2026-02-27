"""
One-time script to get a Google OAuth refresh token for Drive access.

Run this ONCE on your own machine:
    python get_refresh_token.py

It will open a browser window asking you to sign in to the Google account
that owns the IB Papers folder in Drive.  After you approve, it prints your
refresh token — paste that into your .env file as GOOGLE_REFRESH_TOKEN.

Requirements (already in requirements.txt):
    google-auth-oauthlib
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import json, os

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

CLIENT_ID     = input("Paste your Google OAuth Client ID:     ").strip()
CLIENT_SECRET = input("Paste your Google OAuth Client Secret: ").strip()

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=8080)

print("\n✅  Success! Add these three lines to your backend/.env:\n")
print(f"GOOGLE_CLIENT_ID={CLIENT_ID}")
print(f"GOOGLE_CLIENT_SECRET={CLIENT_SECRET}")
print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
print("\nKeep the refresh token secret — it gives read access to your Drive.")
