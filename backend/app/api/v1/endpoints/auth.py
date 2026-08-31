from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import User,Role
from app.core.security import verify_password,create_access_token
from app.schemas.models import LoginRequest,TokenResponse
from app.api.deps import current_user
router=APIRouter()
@router.post("/login",response_model=TokenResponse)
def login(payload:LoginRequest,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=payload.username).first()
    if not u or not u.is_active or not verify_password(payload.password,u.password_hash): raise HTTPException(401,"Incorrect username or password")
    token=create_access_token(u.username); return {"access_token":token,"token_type":"bearer","user":{"id":u.user_id,"username":u.username,"name":u.full_name,"role":u.role.role_name}}
@router.get("/me")
def me(user=Depends(current_user)): return {"id":user.user_id,"username":user.username,"name":user.full_name,"role":user.role.role_name,"email":user.email}
