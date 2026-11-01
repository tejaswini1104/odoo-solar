from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.security import (
    SESSION_COOKIE, SESSION_DAYS, hash_password, hash_token, new_session_token, session_expiry, verify_password
)
from backend.app.models.models import AuthSession, Customer, User
from backend.app.schemas.portal_schemas import LoginRequest, RegisterRequest, UserResponse
from backend.app.schemas.staff_schemas import ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_out(user: User) -> UserResponse:
    return UserResponse(id=user.id, name=user.name, email=user.email, role=user.role, customer_id=user.customer_id)


def _start_session(db: Session, user: User, response: Response) -> None:
    token = new_session_token()
    db.add(AuthSession(user_id=user.id, token_hash=hash_token(token), expires_at=session_expiry()))
    db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,      # JavaScript cannot read the cookie
        samesite="lax",     # not sent on cross-site form posts
        secure=False,       # set to True once the site is served over HTTPS
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please sign in.")

    # Every customer account gets a customer record, so enquiries, tickets and warranties have something to attach to.
    customer = Customer(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        email=email,
        address=payload.address.strip(),
        city=payload.city.strip(),
    )
    db.add(customer)
    db.flush()

    user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone.strip(),
        password_hash=hash_password(payload.password),
        role="customer",
        customer_id=customer.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _start_session(db, user, response)
    return _user_out(user)


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    # Same message whether the email or the password is wrong, so the form does not reveal which accounts exist.
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")

    _start_session(db, user, response)
    return _user_out(user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session_token: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
):
    if session_token:
        db.query(AuthSession).filter(AuthSession.token_hash == hash_token(session_token)).delete()
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    session_token: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Your current password is incorrect.")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="Choose a new password that is different from the current one.")

    user.password_hash = hash_password(payload.new_password)
    # Sign out every other device, but keep this one signed in
    keep = hash_token(session_token) if session_token else None
    others = db.query(AuthSession).filter(AuthSession.user_id == user.id)
    if keep:
        others = others.filter(AuthSession.token_hash != keep)
    others.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=204)
