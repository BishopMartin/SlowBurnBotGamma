"""Custom JWT refresh endpoint — issues a new access token given a valid one."""
from fastapi import APIRouter, Depends
from app.auth import current_active_user, get_jwt_strategy
from app.models.user import User

router = APIRouter(prefix="/auth/jwt", tags=["auth"])


@router.post("/refresh")
async def refresh_token(
    user: User = Depends(current_active_user),
):
    """Exchange a valid access token for a fresh one."""
    strategy = get_jwt_strategy()
    new_token = await strategy.write_token(user)
    return {"access_token": new_token, "token_type": "bearer"}
