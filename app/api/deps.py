# app/api/deps.py
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.config import settings
from app.models.user import User, UserRole
from pydantic import BaseModel

# OAuth2 scheme - extracts token from Authorization header
# tokenUrl is the endpoint where users login to get tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class TokenData(BaseModel):
    """Token payload data - what's inside the JWT token"""
    email: Optional[str] = None


def get_current_user(
    session: Session = Depends(get_session),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency to get the current authenticated user.
    
    How it works:
    1. Extracts JWT token from Authorization header
    2. Decodes and verifies the token
    3. Fetches user from database
    4. Returns User object or raises 401 error
    
    Usage in endpoints:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    
    Args:
        session: Database session
        token: JWT token from Authorization header
    
    Returns:
        User object from database
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Extract email from token
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
        token_data = TokenData(email=email)
        
    except JWTError:
        raise credentials_exception
    
    # Find user in database
    user = session.exec(
        select(User).where(User.email == token_data.email)
    ).first()
    
    if user is None:
        raise credentials_exception
        
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active.
    
    Currently just returns the user, but you can add checks here:
    - if not user.is_active: raise HTTPException(...)
    - if user.is_banned: raise HTTPException(...)
    
    Usage:
        @router.get("/profile")
        def get_profile(user: User = Depends(get_current_active_user)):
            return user
    """
    # Add any additional checks here if needed
    return current_user


def get_current_teacher(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure current user is a teacher.
    
    This is a "guard" - it blocks access if user is not a teacher.
    
    Usage:
        @router.get("/teachers/dashboard")
        def teacher_dashboard(teacher: User = Depends(get_current_teacher)):
            return {"message": "Welcome teacher!"}
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User object (if they are a teacher)
        
    Raises:
        HTTPException: 403 Forbidden if user is not a teacher
    """
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Teacher access required."
        )
    return current_user


def get_current_student(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure current user is a student.
    
    Usage:
        @router.get("/students/schedule")
        def student_schedule(student: User = Depends(get_current_student)):
            return {"message": "Your schedule"}
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User object (if they are a student)
        
    Raises:
        HTTPException: 403 Forbidden if user is not a student
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Student access required."
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure current user is an admin.
    
    Usage:
        @router.get("/admin/users")
        def list_all_users(admin: User = Depends(get_current_admin)):
            return {"users": [...]}
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User object (if they are an admin)
        
    Raises:
        HTTPException: 403 Forbidden if user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Admin access required."
        )
    return current_user


# Test the dependencies (optional - for development)
if __name__ == "__main__":
    print("\n✅ Authentication Dependencies Created!\n")
    print("Available guards:")
    print("  - get_current_user() → Any authenticated user")
    print("  - get_current_active_user() → Active users")
    print("  - get_current_teacher() → Teachers only")
    print("  - get_current_student() → Students only")
    print("  - get_current_admin() → Admins only")
    print("\nReady to protect your endpoints! 🛡️\n")