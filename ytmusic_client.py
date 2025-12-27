# ytmusic_client.py
import os
from ytmusicapi import YTMusic

YTMUSIC_COOKIE = os.environ.get("YTMUSIC_COOKIE")

def get_client() -> YTMusic:
    # YTMUSIC_COOKIE debe contener el contenido del header "Cookie" exportado desde tu navegador
    return YTMusic(headers_raw=YTMUSIC_COOKIE)

def create_playlist_and_add_tracks(title: str, description: str, tracks: list[dict]) -> tuple[str, int, int]:
    """
    tracks: lista de dicts con campos 'name' y 'artists' (lista de nombres).
    Devuelve: (playlist_id, success_count, fail_count)
    """
    ytm = get_client()
    playlist_id = ytm.create_playlist(title=title, description=description, privacy_status="PRIVATE")
    success = 0
    fail = 0
    for track in tracks:
        query = f"{track['name']} {' '.join(track['artists'])}"
        search_results = ytm.search(query, filter="songs")
        if not search_results:
            fail += 1
            continue
        video_id = search_results[0]["videoId"]
        try:
            ytm.add_playlist_items(playlist_id, [video_id])
            success += 1
        except Exception:
            fail += 1
    return playlist_id, success, fail
