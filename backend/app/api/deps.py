from fastapi import Depends,HTTPException,Request,status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.all_models import User
from app.core.config import settings

oauth2=OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
def current_user(request:Request,db:Session=Depends(get_db),token:str=Depends(oauth2))->User:
    try:
        claims=decode_access_token(token)
        username=claims.get("sub")
    except JWTError: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or expired token")
    user=db.query(User).filter_by(username=username,is_active=True).first()
    if not user: raise HTTPException(status_code=401,detail="User not found or inactive")
    if claims.get("pv",0) != user.password_version:
        raise HTTPException(status_code=401,detail="Password changed; sign in again")
    if user.must_change_password and not (
        request.url.path.endswith("/auth/me")
        or request.url.path.endswith("/auth/change-password")
    ):
        raise HTTPException(status_code=403,detail="Password change required before accessing this resource")
    return user
def require_roles(*roles):
    def checker(user:User=Depends(current_user)):
        if user.role.role_name not in roles: raise HTTPException(status_code=403,detail="Insufficient permission")
        return user
    return checker
