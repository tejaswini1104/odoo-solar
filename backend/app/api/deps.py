from datetime import datetime
from typing import Optional, Tuple
from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import SESSION_COOKIE, hash_token
from backend.app.models.models import AuthSession, User

from backend.app.core.roles import ADMIN, CUSTOMER, SALES, STAFF_ROLES, SUPPORT, TECHNICIAN, WAREHOUSE  # noqa: F401

READ_METHODS = ("GET", "HEAD", "OPTIONS")


def get_current_user(
    session_token: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    """Return the signed-in user, or raise 401 if there is no valid session."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not signed in.")

    auth = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(session_token)).first()
    if not auth or auth.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")

    user = db.query(User).filter(User.id == auth.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="This account is not available.")
    return user


def require_customer(user: User = Depends(get_current_user)) -> User:
    """Allow only customer accounts that are linked to a customer record."""
    if user.role != "customer" or user.customer_id is None:
        raise HTTPException(status_code=403, detail="This area is for customer accounts only.")
    return user


def role_gate(read: Tuple[str, ...] = (), write: Tuple[str, ...] = ()):
    """Router-level access rule: `read` roles may use GET requests, `write` roles may change data.

    Customers are never listed, so they cannot reach staff endpoints even when signed in.
    """

    def dependency(request: Request, user: User = Depends(get_current_user)) -> User:
        allowed = read if request.method in READ_METHODS else write
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Your role does not have access to this action.")
        return user

    return dependency


def require_roles(*roles: str):
    """Endpoint-level rule for actions that need a narrower set of roles than their router allows."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Your role does not have access to this action.")
        return user

    return dependency
