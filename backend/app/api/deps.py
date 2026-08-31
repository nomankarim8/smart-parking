from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.database import get_db
from app.core.security import decode_token
from app.models.all_models import User
from app.core.config import settings

oauth2=OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
def current_user(db:Session=Depends(get_db),token:str=Depends(oauth2))->User:
    try: username=decode_token(token)
    except JWTError: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or expired token")
    user=db.query(User).filter_by(username=username,is_active=True).first()
    if not user: raise HTTPException(status_code=401,detail="User not found or inactive")
    return user
def require_roles(*roles):
    def checker(user:User=Depends(current_user)):
        if user.role.role_name not in roles: raise HTTPException(status_code=403,detail="Insufficient permission")
        return user
    return checker
