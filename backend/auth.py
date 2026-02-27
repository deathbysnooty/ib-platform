"""
Authentication helpers.

Students sign in with Google (via the Google Identity Services button on the
frontend).  The frontend receives a Google ID token and POSTs it to
/api/auth/google.  We verify it, then issue our own JWT stored as an
HTTP-only cookie so the browser sends it automatically on every request.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, Security
from fastapi.security import APIKeyCookie
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from models import User

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30

cookie_scheme = APIKeyCookie(name="session", auto_error=False)


def verify_google_token(token: str) -> dict:
    """Verify a Google ID token and return the decoded payload."""
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        return idinfo
    except Exception as e:
        logger.warning(f"Google token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google token")


def create_session_token(user: User) -> str:
    payload = {
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(session: Optional[str] = Security(cookie_scheme)) -> User:
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(session, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return User(
            email=payload["email"],
            name=payload["name"],
            picture=payload.get("picture"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired — please sign in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")
