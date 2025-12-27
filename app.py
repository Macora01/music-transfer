# app.py
import os
from flask import Flask, render_template, redirect, request, session, url_for, flash

from supabase_client import get_service_client
from spotify_client import get_authorize_url, exchange_code_for_token, save_tokens_for_user, get_user_playlists, get_playlist_tracks
from ytmusic_client import create_playlist_and_add_tracks
from auth_middleware import login_required

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me")

@app.route("/")
def index():
    """
    Página inicial muy simple. En una versión real, aquí se integraría el widget de Supabase Auth
    (por ejemplo, un frontend con Supabase JS que al loguear llame a un endpoint para registrar el user_id en session).
    """
    user_id = session.get("user_id")
    return render_template("index.html", user_id=user_id)

@app.route("/mock-login", methods=["GET", "POST"])
def mock_login():
    """
    Solo para pruebas locales: se fija manualmente un user_id.
    Luego se reemplaza por Supabase Auth real.
    """
    if request.method == "POST":
        user_id = request.form.get("user_id")
        if user_id:
            session["user_id"] = user_id
            flash("Sesión iniciada (mock).", "success")
            return redirect(url_for("dashboard"))
        flash("Debes indicar un user_id.", "danger")
    return render_template("mock_login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/auth/spotify/login")
@login_required
def spotify_login():
    state = "xyz"  # se puede generar aleatorio y guardar en session
    url = get_authorize_url(state)
    return redirect(url)

@app.route("/auth/spotify/callback")
@login_required
def spotify_callback():
    error = request.args.get("error")
    if error:
        flash(f"Error de Spotify: {error}", "danger")
        return redirect(url_for("dashboard"))

    code = request.args.get("code")
    if not code:
        flash("Falta 'code' en el callback de Spotify.", "danger")
        return redirect(url_for("dashboard"))

    token_data = exchange_code_for_token(code)
    user_id = session["user_id"]
    save_tokens_for_user(user_id, token_data)
    flash("Spotify conectado correctamente.", "success")
    return redirect(url_for("playlists"))

@app.route("/playlists")
@login_required
def playlists():
    user_id = session["user_id"]
    pls = get_user_playlists(user_id)
    return render_template("playlists.html", playlists=pls)

@app.route("/transfer/<playlist_id>", methods=["POST"])
@login_required
def transfer_playlist(playlist_id):
    user_id = session["user_id"]
    svc = get_service_client()

    # Obtener info de la playlist y sus tracks en Spotify
    playlists = get_user_playlists(user_id)
    playlist = next((p for p in playlists if p["id"] == playlist_id), None)
    if not playlist:
        flash("Playlist no encontrada.", "danger")
        return redirect(url_for("playlists"))

    tracks_raw = get_playlist_tracks(user_id, playlist_id)
    tracks = []
    for item in tracks_raw:
        t = item.get("track")
        if not t:
            continue
        name = t.get("name")
        artists = [a["name"] for a in t.get("artists", [])]
        if not name:
            continue
        tracks.append({"name": name, "artists": artists})

    # Crear playlist en YouTube Music
    title = playlist["name"]
    description = f"Copiada desde Spotify ({playlist_id})"
    target_playlist_id, success_count, fail_count = create_playlist_and_add_tracks(
        title=title,
        description=description,
        tracks=tracks,
    )

    log_payload = {
        "user_id": user_id,
        "source_service": "spotify",
        "target_service": "ytmusic",
        "source_playlist_id": playlist_id,
        "source_playlist_name": playlist["name"],
        "target_playlist_id": target_playlist_id,
        "target_playlist_name": title,
        "total_tracks": len(tracks),
        "success_count": success_count,
        "fail_count": fail_count,
        "status": "finished",
        "message": None,
    }
    svc.table("transfer_logs").insert(log_payload).execute()

    flash(f"Transferencia completa. Éxito: {success_count}, errores: {fail_count}", "success")
    return redirect(url_for("playlists"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5005)
