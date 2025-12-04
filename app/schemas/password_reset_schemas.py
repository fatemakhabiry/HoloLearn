from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password - user provides email"""
    email: EmailStr
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com"
            }
        }
    }

class VerifyOTPRequest(BaseModel):
    """Request schema for verifying OTP code"""
    email: EmailStr
    otp_code: str
    
    @field_validator('otp_code')
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if len(v) != 6:
            raise ValueError('OTP must be exactly 6 digits')
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp_code": "123456"
            }
        }
    }

class ResetPasswordRequest(BaseModel):
    """Request schema for resetting password with OTP"""
    email: EmailStr
    otp_code: str
    new_password: str
    confirm_password: str
    
    @field_validator('otp_code')
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if len(v) != 6:
            raise ValueError('OTP must be exactly 6 digits')
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 50:
            raise ValueError('Password must be less than 50 characters')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp_code": "123456",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!"
            }
        }
    }

class MessageResponse(BaseModel):
    """Generic response with message"""
    message: str
    
class OTPVerificationResponse(BaseModel):
    """Response after OTP verification"""
    message: str
    email: str
    verified: bool