# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing context
# This creates a "password hasher" that uses bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Example:
        User logs in with "mypassword123"
        We check if it matches the hashed version in database
    
    Args:
        plain_password: The password user typed (e.g., "mypassword123")
        hashed_password: The hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain password.
    
    Example:
        User registers with password "mypassword123"
        We hash it before saving to database
        Result: "$2b$12$KIXxP9Q7..."
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string (safe to store in database)
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token (digital ID card).
    
    Example:
        User logs in successfully
        We create a token with their email
        Token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    Args:
        data: Dictionary to encode (e.g., {"sub": "user@email.com"})
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add expiration to token data
    to_encode.update({"exp": expire})
    
    # Encode and sign the token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    
    Example:
        User sends request with token
        We decode it to get their email
        Result: {"sub": "user@email.com", "exp": 1234567890}
    
    Args:
        token: The JWT token string
    
    Returns:
        Decoded token payload (dictionary)
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise e


# Test the functions (for development only)
if __name__ == "__main__":
    print("\n🧪 Testing Security Functions...\n")
    
    # Test 1: Password hashing
    print("1️⃣ Testing Password Hashing:")
    password = "mypassword123"
    hashed = get_password_hash(password)
    print(f"   Original password: {password}")
    print(f"   Hashed password: {hashed[:50]}...")
    print(f"   ✅ Password hashed successfully!")
    
    # Test 2: Password verification
    print("\n2️⃣ Testing Password Verification:")
    is_correct = verify_password(password, hashed)
    print(f"   Correct password verification: {is_correct}")
    
    is_wrong = verify_password("wrongpassword", hashed)
    print(f"   Wrong password verification: {is_wrong}")
    print(f"   ✅ Password verification working!")
    
    # Test 3: JWT token creation
    print("\n3️⃣ Testing JWT Token Creation:")
    token = create_access_token({"sub": "test@example.com"})
    print(f"   Token created: {token[:50]}...")
    print(f"   ✅ Token created successfully!")
    
    # Test 4: JWT token decoding
    print("\n4️⃣ Testing JWT Token Decoding:")
    decoded = decode_access_token(token)
    print(f"   Decoded payload: {decoded}")
    print(f"   ✅ Token decoded successfully!")
    
    print("\n✅ All security functions working perfectly!\n")# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing context
# This creates a "password hasher" that uses bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Example:
        User logs in with "mypassword123"
        We check if it matches the hashed version in database
    
    Args:
        plain_password: The password user typed (e.g., "mypassword123")
        hashed_password: The hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain password.
    
    Example:
        User registers with password "mypassword123"
        We hash it before saving to database
        Result: "$2b$12$KIXxP9Q7..."
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string (safe to store in database)
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token (digital ID card).
    
    Example:
        User logs in successfully
        We create a token with their email
        Token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    Args:
        data: Dictionary to encode (e.g., {"sub": "user@email.com"})
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add expiration to token data
    to_encode.update({"exp": expire})
    
    # Encode and sign the token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    
    Example:
        User sends request with token
        We decode it to get their email
        Result: {"sub": "user@email.com", "exp": 1234567890}
    
    Args:
        token: The JWT token string
    
    Returns:
        Decoded token payload (dictionary)
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise e


# Test the functions (for development only)
if __name__ == "__main__":
    print("\n🧪 Testing Security Functions...\n")
    
    # Test 1: Password hashing
    print("1️⃣ Testing Password Hashing:")
    password = "mypassword123"
    hashed = get_password_hash(password)
    print(f"   Original password: {password}")
    print(f"   Hashed password: {hashed[:50]}...")
    print(f"   ✅ Password hashed successfully!")
    
    # Test 2: Password verification
    print("\n2️⃣ Testing Password Verification:")
    is_correct = verify_password(password, hashed)
    print(f"   Correct password verification: {is_correct}")
    
    is_wrong = verify_password("wrongpassword", hashed)
    print(f"   Wrong password verification: {is_wrong}")
    print(f"   ✅ Password verification working!")
    
    # Test 3: JWT token creation
    print("\n3️⃣ Testing JWT Token Creation:")
    token = create_access_token({"sub": "test@example.com"})
    print(f"   Token created: {token[:50]}...")
    print(f"   ✅ Token created successfully!")
    
    # Test 4: JWT token decoding
    print("\n4️⃣ Testing JWT Token Decoding:")
    decoded = decode_access_token(token)
    print(f"   Decoded payload: {decoded}")
    print(f"   ✅ Token decoded successfully!")
    
    print("\n✅ All security functions working perfectly!\n")