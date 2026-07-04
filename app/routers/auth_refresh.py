"""Access-token reissue endpoint.

Still requires a still-valid access token and hands back a fresh one with
the same lifetime — an expired token cannot be reissued; the bot client
falls back to logging in again (burnBot_apiClient.py's 401-retry path,
which re-authenticates with stored credentials regardless of whether this
endpoint exists).

Unlike the old stateless-JWT design, "still-valid" now means something real:
tokens are DatabaseStrategy-backed (app/auth.py), so a token can also be
invalidated early — via /auth/jwt/logout or a password change — and this
endpoint would then correctly 401 rather than happily reissuing a token that
should already be dead. This also rotates: the old token is revoked as soon
as the new one is minted, so a single access token can't be indefinitely
duplicated by repeated calls here.
"""
from fastapi import APIRouter, Depends, Request
from fastapi_users.authentication.strategy.db import DatabaseStrategy

from app.auth import current_active_user, get_database_strategy
from app.models.user import User

router = APIRouter(prefix="/auth/jwt", tags=["auth"])


@router.post("/refresh")
async def refresh_token(
    request: Request,
    user: User = Depends(current_active_user),
    strategy: DatabaseStrategy = Depends(get_database_strategy),
):
    """Reissue an access token, rotating the old one out."""
    new_token = await strategy.write_token(user)

    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        old_token = auth_header[7:].strip()
        if old_token:
            await strategy.destroy_token(old_token, user)

    return {"access_token": new_token, "token_type": "bearer"}
