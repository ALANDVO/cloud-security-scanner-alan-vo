from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from ..core.database import get_db
from ..core.config import settings
from ..core.security import verify_token
from ..models.domain import Scan, Finding


def get_db_session() -> Generator:
    yield from get_db()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db_session),
) -> dict:
    if not settings.oidc_enabled:
        return {"sub": "local-user", "roles": ["admin"]}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def require_role(allowed_roles: list[str]):
    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_roles = user.get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker