# spotify_client.py
import os
import time
import base64
from datetime import datetime, timedelta
import requests

from supabase_client import get_service_client

SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REDIRECT_URI = os.environ["SPOTIFY_REDIRECT_URI"]

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"

def get_authorize_url(state: str) -> str:
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "false",
    }
    from urllib.parse import urlencode
    return f"{AUTH_URL}?{urlencode(params)}"

def _basic_auth_header() -> dict:
    creds = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64 = base64.b64encode(creds.encode()).decode()
    return {"Authorization": f"Basic {b64}"}

def exchange_code_for_token(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }
    headers = _basic_auth_header()
    resp = requests.post(TOKEN_URL, data=data, headers=headers)
    resp.raise_for_status()
    token = resp.json()
    return token

def refresh_access_token(refresh_token: str) -> dict:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = _basic_auth_header()
    resp = requests.post(TOKEN_URL, data=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def save_tokens_for_user(user_id: str, token_data: dict):
    svc = get_service_client()
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    payload = {
        "user_id": user_id,
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
        "scope": token_data.get("scope"),
        "token_type": token_data.get("token_type"),
        "expires_at": expires_at.isoformat(),
    }
    svc.table("spotify_tokens").upsert(payload, on_conflict="user_id").execute()

def get_valid_access_token(user_id: str) -> str | None:
    svc = get_service_client()
    res = svc.table("spotify_tokens").select("*").eq("user_id", user_id).single().execute()
    data = res.data
    if not data:
        return None
    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    if datetime.utcnow() >= expires_at - timedelta(seconds=60):
        # refresh
        new_token = refresh_access_token(data["refresh_token"])
        if "access_token" in new_token:
            save_tokens_for_user(user_id, new_token)
            return new_token["access_token"]
    return data["access_token"]

def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}

def get_user_playlists(user_id: str) -> list[dict]:
    access_token = get_valid_access_token(user_id)
    if not access_token:
        return []
    headers = _auth_headers(access_token)
    playlists = []
    url = f"{API_BASE}/me/playlists?limit=50"
    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        playlists.extend(data.get("items", []))
        url = data.get("next")
    return playlists

def get_playlist_tracks(user_id: str, playlist_id: str) -> list[dict]:
    access_token = get_valid_access_token(user_id)
    if not access_token:
        return []
    headers = _auth_headers(access_token)
    tracks = []
    url = f"{API_BASE}/playlists/{playlist_id}/tracks?limit=100"
    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        tracks.extend(data.get("items", []))
        url = data.get("next")
    return tracks
