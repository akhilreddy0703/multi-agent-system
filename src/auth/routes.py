"""Auth routes: JWT login."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Form, HTTPException

from src.config import settings
from src.log_config import logger as log

router = APIRouter(prefix="/auth", tags=["auth"])

# Demo credentials for development; override in production
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "password"


@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Issue a JWT access token for valid credentials."""
    if username == DEMO_USERNAME and password == DEMO_PASSWORD:
        payload = {
            "sub": "user_123",
            "username": username,
            "exp": datetime.now(UTC) + timedelta(hours=24),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm="HS256",
        )
        log.info(f"Auth login success user={username}")
        return {"access_token": token, "token_type": "bearer"}
    log.warning(f"Auth login failed user={username}")
    raise HTTPException(status_code=401, detail="Invalid credentials")
