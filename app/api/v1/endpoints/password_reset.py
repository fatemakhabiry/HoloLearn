# # app/api/v1/endpoints/password_reset.py
# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlmodel import Session, select
# import random
# import string
# from datetime import datetime, timedelta
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# import os
# from dotenv import load_dotenv

# from app.core.database import get_session
# from app.core.security import get_password_hash
# from app.models.user import User, OTPVerification
# from app.schemas.password_reset_schemas import (
#     ForgotPasswordRequest, 
#     VerifyOTPRequest, 
#     ResetPasswordRequest,
#     MessageResponse,
#     OTPVerificationResponse
# )

# load_dotenv()

# # Router WITHOUT prefix (prefix is set in router.py)
# router = APIRouter()


# # ===== UTILITY FUNCTIONS =====

# def generate_otp() -> str:
#     """Generate a random 6-digit OTP code"""
#     return ''.join(random.choices(string.digits, k=6))


# def get_otp_expiration_time(minutes: int = 10) -> datetime:
#     """Get expiration datetime for OTP (default: 10 minutes)"""
#     return datetime.utcnow() + timedelta(minutes=minutes)


# def is_otp_expired(expires_at: datetime) -> bool:
#     """Check if OTP has expired"""
#     return datetime.utcnow() > expires_at


# def delete_old_otps(session: Session, email: str):
#     """Delete all previous OTPs for an email (cleanup)"""
#     statement = select(OTPVerification).where(OTPVerification.email == email)
#     old_otps = session.exec(statement).all()
    
#     for otp in old_otps:
#         session.delete(otp)
    
#     session.commit()


# def validate_otp(session: Session, email: str, otp_code: str) -> tuple[bool, str]:
#     """
#     Validate OTP code
    
#     Returns:
#         tuple: (is_valid: bool, message: str)
#     """
#     # Find OTP record
#     statement = select(OTPVerification).where(
#         OTPVerification.email == email,
#         OTPVerification.otp_code == otp_code
#     )
#     otp_record = session.exec(statement).first()
    
#     if not otp_record:
#         return False, "Invalid OTP code"
    
#     if otp_record.is_used:
#         return False, "OTP code has already been used"
    
#     if is_otp_expired(otp_record.expires_at):
#         # Delete expired OTP from database
#         session.delete(otp_record)
#         session.commit()
#         return False, "OTP code has expired"
    
#     return True, "OTP is valid"


# def delete_otp_after_use(session: Session, email: str, otp_code: str):
#     """Delete OTP after successful password reset"""
#     statement = select(OTPVerification).where(
#         OTPVerification.email == email,
#         OTPVerification.otp_code == otp_code
#     )
#     otp_record = session.exec(statement).first()
    
#     if otp_record:
#         session.delete(otp_record)
#         session.commit()


# def send_otp_email(recipient_email: str, otp_code: str, user_name: str = None) -> bool:
#     """Send OTP code via email"""
#     smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
#     smtp_port = int(os.getenv("SMTP_PORT", "587"))
#     sender_email = os.getenv("SENDER_EMAIL")
#     sender_password = os.getenv("SENDER_PASSWORD")
    
#     if not sender_email or not sender_password:
#         print("❌ Email credentials not configured")
#         return False
    
#     try:
#         message = MIMEMultipart("alternative")
#         message["Subject"] = "HoloLearn - Password Reset OTP"
#         message["From"] = sender_email
#         message["To"] = recipient_email
        
#         greeting = f"Hi {user_name}," if user_name else "Hi,"
        
#         text_content = f"""
# {greeting}

# You requested to reset your password for HoloLearn.

# Your OTP code is: {otp_code}

# This code will expire in 10 minutes.

# If you didn't request this, please ignore this email.

# Best regards,
# HoloLearn Team
#         """
        
#         html_content = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
#                 <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
#                     <h2 style="color: #4A90E2;">HoloLearn Password Reset</h2>
#                     <p>{greeting}</p>
#                     <p>You requested to reset your password for HoloLearn.</p>
                    
#                     <div style="background-color: #f4f4f4; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
#                         <p style="margin: 0; font-size: 14px; color: #666;">Your OTP Code:</p>
#                         <h1 style="margin: 10px 0; color: #4A90E2; letter-spacing: 5px; font-size: 36px;">{otp_code}</h1>
#                         <p style="margin: 0; font-size: 12px; color: #999;">This code will expire in 10 minutes</p>
#                     </div>
                    
#                     <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
                    
#                     <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
#                     <p style="color: #999; font-size: 12px;">Best regards,<br>HoloLearn Team</p>
#                 </div>
#             </body>
#         </html>
#         """
        
#         part1 = MIMEText(text_content, "plain")
#         part2 = MIMEText(html_content, "html")
#         message.attach(part1)
#         message.attach(part2)
        
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             server.starttls()
#             server.login(sender_email, sender_password)
#             server.sendmail(sender_email, recipient_email, message.as_string())
        
#         print(f"✅ OTP email sent to {recipient_email}")
#         return True
        
#     except Exception as e:
#         print(f"❌ Error sending email: {str(e)}")
#         return False


# def send_password_reset_success_email(recipient_email: str, user_name: str = None) -> bool:
#     """Send confirmation email after password reset"""
#     smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
#     smtp_port = int(os.getenv("SMTP_PORT", "587"))
#     sender_email = os.getenv("SENDER_EMAIL")
#     sender_password = os.getenv("SENDER_PASSWORD")
    
#     if not sender_email or not sender_password:
#         return False
    
#     try:
#         message = MIMEMultipart("alternative")
#         message["Subject"] = "HoloLearn - Password Reset Successful"
#         message["From"] = sender_email
#         message["To"] = recipient_email
        
#         greeting = f"Hi {user_name}," if user_name else "Hi,"
        
#         text_content = f"""
# {greeting}

# Your password has been successfully reset.

# If you didn't make this change, please contact support immediately.

# Best regards,
# HoloLearn Team
#         """
        
#         html_content = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
#                 <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
#                     <h2 style="color: #4CAF50;">Password Reset Successful</h2>
#                     <p>{greeting}</p>
#                     <p>Your password has been successfully reset.</p>
#                     <p style="color: #666;">If you didn't make this change, please contact support immediately.</p>
#                     <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
#                     <p style="color: #999; font-size: 12px;">Best regards,<br>HoloLearn Team</p>
#                 </div>
#             </body>
#         </html>
#         """
        
#         part1 = MIMEText(text_content, "plain")
#         part2 = MIMEText(html_content, "html")
#         message.attach(part1)
#         message.attach(part2)
        
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             server.starttls()
#             server.login(sender_email, sender_password)
#             server.sendmail(sender_email, recipient_email, message.as_string())
        
#         return True
        
#     except Exception as e:
#         print(f"❌ Error sending confirmation email: {str(e)}")
#         return False


# # ===== API ENDPOINTS =====

# @router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
# async def request_password_reset(
#     request: ForgotPasswordRequest,
#     session: Session = Depends(get_session)
# ):
#     """
#     Request password reset - sends OTP to user's email
    
#     Steps:
#     1. Check if user exists
#     2. Delete any old OTPs for this email
#     3. Generate new 6-digit OTP
#     4. Save OTP to database with 10-minute expiration
#     5. Send OTP via email
#     """
    
#     # Check if user exists
#     statement = select(User).where(User.email == request.email)
#     user = session.exec(statement).first()
    
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No account found with this email address"
#         )
    
#     # Delete old OTPs for this email
#     delete_old_otps(session, request.email)
    
#     # Generate new OTP
#     otp_code = generate_otp()
#     expires_at = get_otp_expiration_time(minutes=10)
    
#     # Save OTP to database
#     otp_record = OTPVerification(
#         email=request.email,
#         otp_code=otp_code,
#         expires_at=expires_at
#     )
#     session.add(otp_record)
#     session.commit()
    
#     # Send OTP via email
#     email_sent = send_otp_email(
#         recipient_email=request.email,
#         otp_code=otp_code,
#         user_name=user.full_name
#     )
    
#     if not email_sent:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to send OTP email. Please try again."
#         )
    
#     return MessageResponse(
#         message=f"OTP code has been sent to {request.email}. Please check your email."
#     )


# @router.post("/verify-otp", response_model=OTPVerificationResponse, status_code=status.HTTP_200_OK)
# async def verify_otp_code(
#     request: VerifyOTPRequest,
#     session: Session = Depends(get_session)
# ):
#     """
#     Verify OTP code without resetting password
    
#     This endpoint allows the Flutter app to verify if the OTP is valid
#     before proceeding to the password reset screen
#     """
    
#     is_valid, message = validate_otp(session, request.email, request.otp_code)
    
#     if not is_valid:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=message
#         )
    
#     return OTPVerificationResponse(
#         message="OTP verified successfully",
#         email=request.email,
#         verified=True
#     )


# @router.post("/reset-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
# async def reset_password_with_otp(
#     request: ResetPasswordRequest,
#     session: Session = Depends(get_session)
# ):
#     """
#     Reset password using OTP
    
#     Steps:
#     1. Validate OTP
#     2. Check if user exists
#     3. Update user's password
#     4. Mark OTP as used
#     5. Send confirmation email
#     """
    
#     # Validate OTP
#     is_valid, message = validate_otp(session, request.email, request.otp_code)
    
#     if not is_valid:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=message
#         )
    
#     # Get user from database
#     statement = select(User).where(User.email == request.email)
#     user = session.exec(statement).first()
    
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     # Update password
#     user.hashed_password = get_password_hash(request.new_password)
#     session.add(user)
#     session.commit()
#     session.refresh(user)
    
#     # Delete OTP after successful use
#     delete_otp_after_use(session, request.email, request.otp_code)
    
#     # Send confirmation email
#     send_password_reset_success_email(
#         recipient_email=request.email,
#         user_name=user.full_name
#     )
    
#     return MessageResponse(
#         message="Password has been reset successfully. You can now login with your new password."
#     )


# @router.post("/resend-otp", response_model=MessageResponse, status_code=status.HTTP_200_OK)
# async def resend_otp(
#     request: ForgotPasswordRequest,
#     session: Session = Depends(get_session)
# ):
#     """
#     Resend OTP code if user didn't receive it or it expired
    
#     This is essentially the same as forgot-password endpoint
#     """
    
#     # Delete old OTPs
#     delete_old_otps(session, request.email)
    
#     # Generate new OTP
#     otp_code = generate_otp()
#     expires_at = get_otp_expiration_time(minutes=1)
    
#     # Save OTP to database
#     otp_record = OTPVerification(
#         email=request.email,
#         otp_code=otp_code,
#         expires_at=expires_at
#     )
#     session.add(otp_record)
#     session.commit()
    
#     # Get user for name
#     statement = select(User).where(User.email == request.email)
#     user = session.exec(statement).first()
#     user_name = user.full_name if user else None
    
#     # Send OTP via email
#     email_sent = send_otp_email(
#         recipient_email=request.email,
#         otp_code=otp_code,
#         user_name=user_name
#     )
    
#     if not email_sent:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to send OTP email. Please try again."
#         )
    
#     return MessageResponse(
#         message=f"New OTP code has been sent to {request.email}"
#     )


# app/api/v1/endpoints/password_reset.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
import random
import string
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

from app.core.database import get_session
from app.core.security import get_password_hash, verify_password
from app.models.user import User, OTPVerification
from app.schemas.password_reset_schemas import (
    ForgotPasswordRequest, 
    VerifyOTPRequest, 
    ResetPasswordRequest,
    ChangePasswordRequest,
    MessageResponse,
    OTPVerificationResponse
)

load_dotenv()

# Router WITHOUT prefix (prefix is set in router.py)
router = APIRouter()


# ===== UTILITY FUNCTIONS =====

def generate_otp() -> str:
    """Generate a random 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=6))


def get_otp_expiration_time(minutes: int = 10) -> datetime:
    """Get expiration datetime for OTP (default: 10 minutes)"""
    return datetime.utcnow() + timedelta(minutes=minutes)


def is_otp_expired(expires_at: datetime) -> bool:
    """Check if OTP has expired"""
    return datetime.utcnow() > expires_at


def delete_old_otps(session: Session, email: str):
    """Delete all previous OTPs for an email (cleanup)"""
    statement = select(OTPVerification).where(OTPVerification.email == email)
    old_otps = session.exec(statement).all()
    
    for otp in old_otps:
        session.delete(otp)
    
    session.commit()


def validate_otp(session: Session, email: str, otp_code: str) -> tuple[bool, str]:
    """
    Validate OTP code
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    # Find OTP record
    statement = select(OTPVerification).where(
        OTPVerification.email == email,
        OTPVerification.otp_code == otp_code
    )
    otp_record = session.exec(statement).first()
    
    if not otp_record:
        return False, "Invalid OTP code"
    
    if otp_record.is_used:
        return False, "OTP code has already been used"
    
    if is_otp_expired(otp_record.expires_at):
        # Delete expired OTP from database
        session.delete(otp_record)
        session.commit()
        return False, "OTP code has expired"
    
    return True, "OTP is valid"


def delete_otp_after_use(session: Session, email: str, otp_code: str):
    """Delete OTP after successful password reset"""
    statement = select(OTPVerification).where(
        OTPVerification.email == email,
        OTPVerification.otp_code == otp_code
    )
    otp_record = session.exec(statement).first()
    
    if otp_record:
        session.delete(otp_record)
        session.commit()


def send_otp_email(recipient_email: str, otp_code: str, user_name: str = None) -> bool:
    """Send OTP code via email"""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        print("❌ Email credentials not configured")
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "HoloLearn - Password Reset OTP"
        message["From"] = sender_email
        message["To"] = recipient_email
        
        greeting = f"Hi {user_name}," if user_name else "Hi,"
        
        text_content = f"""
{greeting}

You requested to reset your password for HoloLearn.

Your OTP code is: {otp_code}

This code will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
HoloLearn Team
        """
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4A90E2;">HoloLearn Password Reset</h2>
                    <p>{greeting}</p>
                    <p>You requested to reset your password for HoloLearn.</p>
                    
                    <div style="background-color: #f4f4f4; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                        <p style="margin: 0; font-size: 14px; color: #666;">Your OTP Code:</p>
                        <h1 style="margin: 10px 0; color: #4A90E2; letter-spacing: 5px; font-size: 36px;">{otp_code}</h1>
                        <p style="margin: 0; font-size: 12px; color: #999;">This code will expire in 10 minutes</p>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">Best regards,<br>HoloLearn Team</p>
                </div>
            </body>
        </html>
        """
        
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        
        print(f"✅ OTP email sent to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False


def send_password_reset_success_email(recipient_email: str, user_name: str = None) -> bool:
    """Send confirmation email after password reset"""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "HoloLearn - Password Reset Successful"
        message["From"] = sender_email
        message["To"] = recipient_email
        
        greeting = f"Hi {user_name}," if user_name else "Hi,"
        
        text_content = f"""
{greeting}

Your password has been successfully reset.

If you didn't make this change, please contact support immediately.

Best regards,
HoloLearn Team
        """
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4CAF50;">Password Reset Successful</h2>
                    <p>{greeting}</p>
                    <p>Your password has been successfully reset.</p>
                    <p style="color: #666;">If you didn't make this change, please contact support immediately.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">Best regards,<br>HoloLearn Team</p>
                </div>
            </body>
        </html>
        """
        
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        
        return True
        
    except Exception as e:
        print(f"❌ Error sending confirmation email: {str(e)}")
        return False


# ===== API ENDPOINTS =====

@router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def request_password_reset(
    request: ForgotPasswordRequest,
    session: Session = Depends(get_session)
):
    """
    Request password reset - sends OTP to user's email
    
    Steps:
    1. Check if user exists
    2. Delete any old OTPs for this email
    3. Generate new 6-digit OTP
    4. Save OTP to database with 10-minute expiration
    5. Send OTP via email
    """
    
    # Check if user exists
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address"
        )
    
    # Delete old OTPs for this email
    delete_old_otps(session, request.email)
    
    # Generate new OTP
    otp_code = generate_otp()
    expires_at = get_otp_expiration_time(minutes=10)
    
    # Save OTP to database
    otp_record = OTPVerification(
        email=request.email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    session.add(otp_record)
    session.commit()
    
    # Send OTP via email
    email_sent = send_otp_email(
        recipient_email=request.email,
        otp_code=otp_code,
        user_name=user.full_name
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please try again."
        )
    
    return MessageResponse(
        message=f"OTP code has been sent to {request.email}. Please check your email."
    )


@router.post("/verify-otp", response_model=OTPVerificationResponse, status_code=status.HTTP_200_OK)
async def verify_otp_code(
    request: VerifyOTPRequest,
    session: Session = Depends(get_session)
):
    """
    Verify OTP code without resetting password
    
    This endpoint allows the Flutter app to verify if the OTP is valid
    before proceeding to the password reset screen
    """
    
    is_valid, message = validate_otp(session, request.email, request.otp_code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return OTPVerificationResponse(
        message="OTP verified successfully",
        email=request.email,
        verified=True
    )


@router.post("/reset-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def reset_password_with_otp(
    request: ResetPasswordRequest,
    session: Session = Depends(get_session)
):
    """
    Reset password using OTP
    
    Steps:
    1. Validate OTP
    2. Check if user exists
    3. Update user's password
    4. Mark OTP as used
    5. Send confirmation email
    """
    
    # Validate OTP
    is_valid, message = validate_otp(session, request.email, request.otp_code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Get user from database
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Delete OTP after successful use
    delete_otp_after_use(session, request.email, request.otp_code)
    
    # Send confirmation email
    send_password_reset_success_email(
        recipient_email=request.email,
        user_name=user.full_name
    )
    
    return MessageResponse(
        message="Password has been reset successfully. You can now login with your new password."
    )


@router.post("/resend-otp", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def resend_otp(
    request: ForgotPasswordRequest,
    session: Session = Depends(get_session)
):
    """
    Resend OTP code if user didn't receive it or it expired
    
    This is essentially the same as forgot-password endpoint
    """
    
    # Delete old OTPs
    delete_old_otps(session, request.email)
    
    # Generate new OTP
    otp_code = generate_otp()
    expires_at = get_otp_expiration_time(minutes=1)
    
    # Save OTP to database
    otp_record = OTPVerification(
        email=request.email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    session.add(otp_record)
    session.commit()
    
    # Get user for name
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()
    user_name = user.full_name if user else None
    
    # Send OTP via email
    email_sent = send_otp_email(
        recipient_email=request.email,
        otp_code=otp_code,
        user_name=user_name
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please try again."
        )
    
    return MessageResponse(
        message=f"New OTP code has been sent to {request.email}"
    )


@router.post("/change-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def change_password(
    request: ChangePasswordRequest,
    session: Session = Depends(get_session)
):
    """
    Change password for authenticated user
    
    Steps:
    1. Find user by email
    2. Verify old password is correct
    3. Update to new password
    4. Send confirmation email
    """
    
    # Find user by email
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify old password
    if not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password is different from old password
    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Send confirmation email
    send_password_reset_success_email(
        recipient_email=request.email,
        user_name=user.full_name
    )
    
    return MessageResponse(
        message="Password changed successfully"
    )