# auth_middleware.py
from functools import wraps
from flask import request, redirect, url_for, session

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            # TODO: integrar realmente con Supabase Auth (ver nota en app.py)
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper
