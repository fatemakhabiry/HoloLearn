from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.api.deps import get_current_user
from app.models.user import User, UserPublic, UserUpdate,UserBase

router = APIRouter()

@router.get("/me", response_model=UserBase)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current logged-in user's profile.
    
    **Authentication Required:** Yes (any role)
    
    **Returns:** User information (without password)
    """
    return current_user

@router.put("/me", response_model=UserBase)
def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Update current user's profile.
    
    **Authentication Required:** Yes (any role)
    
    **Updatable Fields:**
    - email
    - full_name
    """
    # Update only provided fields
    user_data = user_update.model_dump(exclude_unset=True)
    for key, value in user_data.items():
        setattr(current_user, key, value)
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user