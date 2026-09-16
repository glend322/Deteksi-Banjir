import secrets
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, SavedLocation
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserProfile, SavedLocationResponse

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login-form")

VERIFICATION_TOKEN_EXPIRY_HOURS = 24
RESET_TOKEN_EXPIRY_HOURS = 1

def build_user_profile(user: User, db: Session) -> UserProfile:
    # Query saved locations with coordinates
    saved_locs_query = db.query(
        SavedLocation.id,
        SavedLocation.user_id,
        SavedLocation.name,
        SavedLocation.address,
        SavedLocation.icon,
        SavedLocation.created_at,
        func.ST_Y(SavedLocation.geom).label("lat"),
        func.ST_X(SavedLocation.geom).label("lng")
    ).filter(SavedLocation.user_id == user.id).all()

    saved_locs = [
        SavedLocationResponse(
            id=loc.id,
            user_id=loc.user_id,
            name=loc.name,
            address=loc.address,
            icon=loc.icon,
            lat=loc.lat,
            lng=loc.lng,
            created_at=loc.created_at
        )
        for loc in saved_locs_query
    ]

    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        vehicle_type=user.vehicle_type,
        vehicle_max_depth_cm=user.vehicle_max_depth_cm,
        trust_score=user.trust_score if user.trust_score is not None else 50,
        total_reports=user.total_reports if user.total_reports is not None else 0,
        verified_reports=user.verified_reports if user.verified_reports is not None else 0,
        saved_locations=saved_locs,
        created_at=user.created_at
    )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tidak dapat memvalidasi kredensial login",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: Hanya user dengan is_admin=True yang diizinkan."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Diperlukan hak admin."
        )
    return current_user

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar. Silakan login.")

    verification_token = secrets.token_urlsafe(48)
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRY_HOURS)

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        vehicle_type=payload.vehicle_type,
        vehicle_max_depth_cm=payload.vehicle_max_depth_cm,
        avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
        verification_token=verification_token,
        verification_token_expires=verification_expires,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(
        f"[AUTH] Verification token for {user.email}: {verification_token}"
    )

    access_token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=build_user_profile(user, db)
    )

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email atau password salah")

    access_token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=build_user_profile(user, db)
    )

@router.post("/login-form")
@limiter.limit("10/minute")
def login_form(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Untuk kompatibilitas Swagger UI Authorize button
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email atau password salah")

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh-token", response_model=TokenResponse)
def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh JWT token tanpa login ulang.
    Client mengirim token lama (masih valid) via Authorization header,
    dan mendapatkan token baru dengan expiry yang diperbarui.
    """
    new_token = create_access_token(subject=current_user.id)
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user=build_user_profile(current_user, db)
    )


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, description="Password baru minimal 6 karakter")


@router.put("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ganti password user. Membutuhkan password lama yang benar untuk verifikasi.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password lama tidak sesuai."
        )

    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru tidak boleh sama dengan password lama."
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password berhasil diubah. Silakan login kembali dengan password baru."}


# ─────────────────────────────────────────────────────────────────────────────
# Email Verification
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/request-verification", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def request_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kirim ulang email verifikasi. Token baru dibuat dan yang lama invalid."""
    if current_user.email_verified:
        return {"message": "Email sudah terverifikasi.", "already_verified": True}

    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRY_HOURS)

    current_user.verification_token = token
    current_user.verification_token_expires = expires
    db.commit()

    logger.info(
        f"[AUTH] Verification token for {current_user.email}: {token}"
    )

    return {
        "message": "Token verifikasi berhasil dibuat. Cek log server untuk token (integrasi email belum tersedia).",
        "token": token,
    }


@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(
    token: str = Query(..., description="Token verifikasi dari email"),
    db: Session = Depends(get_db),
):
    """Verifikasi email menggunakan token yang dikirim ke email user."""
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token verifikasi tidak valid.")

    if user.verification_token_expires:
        expires = user.verification_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(status_code=400, detail="Token verifikasi sudah kedaluwarsa. Silakan minta token baru.")

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()

    return {"message": "Email berhasil diverifikasi."}


# ─────────────────────────────────────────────────────────────────────────────
# Password Reset
# ─────────────────────────────────────────────────────────────────────────────

class RequestPasswordResetRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, description="Password baru minimal 6 karakter")


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
def request_password_reset(
    request: Request,
    payload: RequestPasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Minta reset password. Selalu return success untuk mencegah email enumeration.
    Token di-log ke server (integrasi email belum tersedia).
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if user:
        token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRY_HOURS)

        user.reset_token = token
        user.reset_token_expires = expires
        db.commit()

        logger.info(f"[AUTH] Password reset token for {user.email}: {token}")

    # Selalu return success — jangan bocorkan apakah email terdaftar
    return {
        "message": "Jika email terdaftar, instruksi reset password telah dikirim.",
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset password menggunakan token dari email."""
    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token reset tidak valid.")

    if user.reset_token_expires:
        expires = user.reset_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(status_code=400, detail="Token reset sudah kedaluwarsa. Silakan minta token baru.")

    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password berhasil direset. Silakan login dengan password baru."}
