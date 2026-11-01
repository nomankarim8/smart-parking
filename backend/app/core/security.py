from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context=CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password:str)->str: return pwd_context.hash(password)
def verify_password(plain:str, hashed:str)->bool: return pwd_context.verify(plain, hashed)
def create_access_token(subject:str, password_version:int=0)->str:
    exp=datetime.now(timezone.utc)+timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub":subject,"pv":password_version,"exp":exp},settings.SECRET_KEY,algorithm=settings.ALGORITHM)

def create_camera_stream_ticket(subject: str, camera_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": subject,
            "scope": "camera:stream",
            "camera_id": camera_id,
            "iat": now,
            "exp": now + timedelta(seconds=60),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

def decode_token(token:str)->str:
    payload=jwt.decode(token,settings.SECRET_KEY,algorithms=[settings.ALGORITHM])
    sub=payload.get("sub")
    if not sub: raise JWTError("Missing subject")
    return str(sub)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
