
# from datetime import timedelta
# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlmodel import Session, select
# from pydantic import BaseModel

# from app.core.database import get_session
# from app.core.security import verify_password, create_access_token
# from app.core.config import settings
# from app.models.user import User,UserBase

# router = APIRouter()

# # class LoginRequest(BaseModel):
# #     """JSON body for login"""
# #     email: str
# #     password: str


# class Token(BaseModel):
#     """Token response model"""
#     access_token: str
#     token_type: str
#     user: UserBase


# @router.post("/login", response_model=Token)
# def login(
#     form_data: OAuth2PasswordRequestForm = Depends(),
#     session: Session = Depends(get_session)
# ):

#     # Step 1: Find user by email
#     user = session.exec(
#         select(User).where(User.email == form_data.username)
#     ).first()
    
#     # Step 2: Verify credentials
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     if not verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     # Step 2b: Block deactivated accounts
#     if not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Account is deactivated. Contact your administrator.",
#         )
    
#     # Step 3: Create access token
#     access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user.email},
#         expires_delta=access_token_expires
#     )
    
#     # Step 4: Return token and user info
#     return {
#         "access_token": access_token,
#         "token_type": "bearer",
#         "user": user
#     }

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_session
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.models.user import User, UserBase
from app.models.lecture import Lecture
from app.models.agent_session import AgentSession  # adjust import path as needed

router = APIRouter()


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    user: UserBase
    latest_session_id: Optional[int] = None  # None for students/admins


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

    # Step 2b: Block deactivated accounts
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    # Step 3: Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    # Step 4: Fetch latest session ID for teacher only
    latest_session_id = None
    if user.role == "TEACHER":
        latest_session = session.exec(
            select(AgentSession)
            .join(Lecture, AgentSession.lecture_id == Lecture.lecture_id)
            .where(Lecture.teacher_id == user.user_id)
            .order_by(AgentSession.created_at.desc())
            .limit(1)
        ).first()

        latest_session_id = latest_session.id if latest_session else None

    # Step 5: Return token, user info, and latest session ID
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
        "latest_session_id": latest_session_id
    }