from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import User,Role
from app.core.security import verify_password,create_access_token
from app.schemas.models import LoginRequest,TokenResponse
from app.api.deps import current_user
from app.schemas.models import PasswordChange
from app.core.security import hash_password
from app.services.activity import record_activity
router=APIRouter()
@router.post("/login",response_model=TokenResponse)
def login(payload:LoginRequest,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=payload.username).first()
    if not u or not u.is_active or not verify_password(payload.password,u.password_hash): raise HTTPException(401,"Incorrect username or password")
    token=create_access_token(u.username); return {"access_token":token,"token_type":"bearer","user":{"id":u.user_id,"username":u.username,"name":u.full_name,"role":u.role.role_name}}
@router.get("/me")
def me(user=Depends(current_user)): return {"id":user.user_id,"username":user.username,"name":user.full_name,"role":user.role.role_name,"email":user.email}

@router.post("/change-password")
def change_password(payload:PasswordChange,db:Session=Depends(get_db),user=Depends(current_user)):
    if not verify_password(payload.current_password,user.password_hash):
        raise HTTPException(400,"Current password is incorrect")
    if payload.current_password==payload.new_password:
        raise HTTPException(422,"New password must differ from the current password")
    if not any(char.islower() for char in payload.new_password) or not any(char.isupper() for char in payload.new_password) or not any(char.isdigit() for char in payload.new_password):
        raise HTTPException(422,"New password must include upper-case, lower-case, and numeric characters")
    user.password_hash=hash_password(payload.new_password)
    record_activity(db,user.user_id,"PASSWORD_CHANGED","USER",user.user_id,{"outcome":"SUCCESS"})
    db.commit()
    return {"message":"Password changed successfully"}
