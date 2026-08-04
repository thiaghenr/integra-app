from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import get_db, require_api_key
from app.backend.core.security import create_jwt
from app.backend.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


class TokenRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/token", response_model=TokenResponse)
async def get_token(body: TokenRequest, session: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService(session).authenticate_global(body.email, body.password)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from None
    return TokenResponse(access_token=create_jwt(user.id))


@router.get("/auth/token-by-phone", response_model=TokenResponse, dependencies=[Depends(require_api_key)])
async def get_token_by_phone(phone: str = Query(...), session: AsyncSession = Depends(get_db)):
    user = await AuthService(session).authenticate_by_phone(phone)
    return TokenResponse(access_token=create_jwt(user.id))
