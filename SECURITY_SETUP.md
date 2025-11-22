# 🔐 Security Setup Documentation

## Overview
This document explains the security layer for HoloLearn API authentication.

---

## 📁 Files Created

### 1. `app/core/security.py`
Contains password hashing and JWT token functions.

### 2. `app/api/deps.py`
Contains authentication dependencies (guards) for protecting endpoints.

### 3. `.env`
Contains secret configuration (never commit to Git!)

---

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Security Settings
SECRET_KEY=<your-64-character-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/hololearn

# App Settings
APP_NAME=HoloLearn
DEBUG=True
```

**Important:** 
- The SECRET_KEY is generated using: `python -c "import secrets; print(secrets.token_hex(32))"`
- Never share or commit the `.env` file!

---

## 🔧 Security Functions

### File: `app/core/security.py`

#### Password Functions

**1. `get_password_hash(password: str) -> str`**
- Hashes a plain password
- Use when: User registers
- Example:
```python
  hashed = get_password_hash("mypassword123")
  # Result: "$2b$12$KIXxP9Q7..."
```

**2. `verify_password(plain_password: str, hashed_password: str) -> bool`**
- Verifies password matches hash
- Use when: User logs in
- Example:
```python
  is_valid = verify_password("mypassword123", hashed_from_db)
  # Result: True or False
```

#### Token Functions

**3. `create_access_token(data: dict, expires_delta: Optional[timedelta]) -> str`**
- Creates JWT token
- Use when: User logs in successfully
- Example:
```python
  token = create_access_token({"sub": "user@email.com"})
  # Result: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**4. `decode_access_token(token: str) -> dict`**
- Decodes and verifies JWT token
- Use when: Validating user requests
- Example:
```python
  payload = decode_access_token(token)
  # Result: {"sub": "user@email.com", "exp": 1234567890}
```

---

## 🛡️ Authentication Dependencies

### File: `app/api/deps.py`

#### Available Guards

**1. `get_current_user`**
- Gets any authenticated user
- Use for: Endpoints requiring login
- Example:
```python
  @router.get("/profile")
  def get_profile(current_user: User = Depends(get_current_user)):
      return {"email": current_user.email}
```

**2. `get_current_teacher`**
- Ensures user is a teacher
- Returns 403 if not a teacher
- Example:
```python
  @router.get("/teachers/dashboard")
  def teacher_dashboard(teacher: User = Depends(get_current_teacher)):
      return {"message": "Welcome teacher!"}
```

**3. `get_current_student`**
- Ensures user is a student
- Returns 403 if not a student
- Example:
```python
  @router.get("/students/grades")
  def get_grades(student: User = Depends(get_current_student)):
      return {"grades": [...]}
```

**4. `get_current_admin`**
- Ensures user is an admin
- Returns 403 if not an admin
- Example:
```python
  @router.get("/admin/users")
  def list_users(admin: User = Depends(get_current_admin)):
      return {"users": [...]}
```

---

## 🔄 Token Flow

### 1. User Registration
```
User sends: email + password
→ Hash password with get_password_hash()
→ Save user to database
→ Return success
```

### 2. User Login
```
User sends: email + password
→ Find user in database
→ Verify password with verify_password()
→ Create token with create_access_token({"sub": email})
→ Return token to user
```

### 3. Protected Request
```
User sends request with header: Authorization: Bearer <token>
→ get_current_user extracts token
→ Decode and verify token
→ Fetch user from database
→ Endpoint receives user object
```

---

## 🚀 Usage for Person B

### How to use in your endpoints:

#### Public Endpoint (no authentication)
```python
@router.get("/public")
def public_route():
    return {"message": "Anyone can access this"}
```

#### Protected Endpoint (login required)
```python
@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.full_name}!"}
```

#### Role-based Endpoint (teacher only)
```python
@router.get("/teachers/classes")
def get_classes(teacher: User = Depends(get_current_teacher)):
    return {"teacher": teacher.full_name, "classes": [...]}
```

---

## 📦 Required Packages
```
python-jose[cryptography]
passlib[bcrypt]  # or passlib[argon2]
python-multipart
pydantic-settings
```

Install with:
```bash
pip install -r requirements.txt
```

---

## ✅ Testing

### Test security functions:
```bash
python -m app.core.security
```

### Test authentication dependencies:
```bash
python -m app.api.deps
```

---

## 🔒 Security Best Practices

1. ✅ **Never commit `.env`** - It's in `.gitignore`
2. ✅ **Use strong SECRET_KEY** - Generated with 32 random bytes
3. ✅ **Hash passwords** - Never store plain passwords
4. ✅ **Set token expiration** - Tokens expire after 30 minutes
5. ✅ **Use HTTPS in production** - Encrypt all traffic

---

## 🐛 Troubleshooting

### Problem: "Could not validate credentials"
- Token might be expired (30 min expiration)
- Token might be invalid
- User might not exist in database

### Problem: "Not authorized. Teacher access required"
- User is logged in but not a teacher
- Check user.role in database

---

## 📞 Questions?

Contact Person A (Security Foundation Lead) for:
- SECRET_KEY issues
- Token generation problems
- Password hashing questions
- Authentication dependency usage

---

## 🎯 Next Steps for Person B

Now you can:
1. ✅ Create authentication endpoints (`/register`, `/login`)
2. ✅ Create protected user endpoints (`/users/me`)
3. ✅ Create teacher endpoints (`/teachers/me`)
4. ✅ Create student endpoints (`/students/me`)

Refer to the task document for Person B's tasks!

---

**Security Layer Complete! 🎉**