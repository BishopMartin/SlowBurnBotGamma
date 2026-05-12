"""Access-token reissue endpoint.

This is NOT a real OAuth refresh-token flow — it requires a still-valid
access token and hands back a fresh one with the same lifetime.  An expired
token cannot be reissued; the bot client falls back to logging in again.

TODO(real-refresh-tokens): introduce a dedicated long-lived refresh token
issued at /auth/jwt/login, stored server-side (or as a JTI allowlist) so it
can be revoked, rotated on each /refresh call, and accepted here in place
of the access token.  Bot client at bot-client/burnBot_apiClient.py:102-121
will need to track and submit it.
"""
from fastapi import APIRouter, Depends
from app.auth import current_active_user, get_jwt_strategy
from app.models.user import User

router = APIRouter(prefix="/auth/jwt", tags=["auth"])


@router.post("/refresh")
async def refresh_token(
    user: User = Depends(current_active_user),
):
    """Reissue an access token.  Caller must still hold a valid one."""
    strategy = get_jwt_strategy()
    new_token = await strategy.write_token(user)
    return {"access_token": new_token, "token_type": "bearer"}
