
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.database import get_session
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.models.user import User,UserBase

router = APIRouter()

# class LoginRequest(BaseModel):
#     """JSON body for login"""
#     email: str
#     password: str


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    user: UserBase


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):

    # Step 1: Find user by email
    user = session.exec(
        select(User).where(User.email == form_data.username)
    ).first()
    
    # Step 2: Verify credentials
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 3: Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    # Step 4: Return token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
