"""
Authentication endpoints – register and login.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import Token, UserCreate, UserLogin, UserOut
from app.services import crm_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new CRM user",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await crm_service.get_user_by_username(db, payload.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' is already taken",
        )
    user = await crm_service.create_user(
        db,
        username=payload.username,
        password=payload.password,
        role=payload.role,
    )
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive a JWT",
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    user = await crm_service.authenticate_user(
        db, payload.username, payload.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(data={"sub": user.username, "role": user.role.value})
    return Token(access_token=token)
