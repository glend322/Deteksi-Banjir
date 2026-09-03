from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, SavedLocation
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserProfile, SavedLocationResponse

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login-form")

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

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar. Silakan login.")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        vehicle_type=payload.vehicle_type,
        vehicle_max_depth_cm=payload.vehicle_max_depth_cm,
        avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=build_user_profile(user, db)
    )

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
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
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Untuk kompatibilitas Swagger UI Authorize button
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email atau password salah")

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

