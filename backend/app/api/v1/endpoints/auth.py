from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import User,Role
from app.core.security import verify_password,create_access_token
from app.schemas.models import LoginRequest,TokenResponse
from app.api.deps import current_user
from app.schemas.models import PasswordChange
from app.core.security import hash_password, verify_password
from app.services.activity import record_activity
from app.models.all_models import PasswordHistory
from app.core.config import settings
from datetime import datetime
router=APIRouter()
@router.post("/login",response_model=TokenResponse)
def login(payload:LoginRequest,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=payload.username).first()
    if not u or not u.is_active or not verify_password(payload.password,u.password_hash): raise HTTPException(401,"Incorrect username or password")
    token=create_access_token(u.username,u.password_version); return {"access_token":token,"token_type":"bearer","user":{"id":u.user_id,"username":u.username,"name":u.full_name,"role":u.role.role_name,"must_change_password":u.must_change_password}}
@router.get("/me")
def me(user=Depends(current_user)): return {"id":user.user_id,"username":user.username,"name":user.full_name,"role":user.role.role_name,"email":user.email,"must_change_password":user.must_change_password}

@router.post("/change-password")
def change_password(payload:PasswordChange,db:Session=Depends(get_db),user=Depends(current_user)):
    if not verify_password(payload.current_password,user.password_hash):
        raise HTTPException(400,"Current password is incorrect")
    if len(payload.new_password)<settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(422,f"New password must contain at least {settings.PASSWORD_MIN_LENGTH} characters")
    if payload.current_password==payload.new_password:
        raise HTTPException(422,"New password must differ from the current password")
    if not (
        any(char.islower() for char in payload.new_password)
        and any(char.isupper() for char in payload.new_password)
        and any(char.isdigit() for char in payload.new_password)
        and any(not char.isalnum() for char in payload.new_password)
    ):
        raise HTTPException(422,"New password must include upper-case, lower-case, numeric, and special characters")
    prior_hashes = [user.password_hash]
    prior_hashes.extend(
        row.password_hash
        for row in db.query(PasswordHistory)
        .filter_by(user_id=user.user_id)
        .order_by(PasswordHistory.history_id.desc())
        .limit(5)
        .all()
    )
    if any(verify_password(payload.new_password, password_hash) for password_hash in prior_hashes):
        raise HTTPException(422,"New password must not reuse a recent password")
    old_hash=user.password_hash
    user.password_hash=hash_password(payload.new_password)
    user.password_changed_at=datetime.utcnow()
    user.password_version+=1
    user.must_change_password=False
    db.add(PasswordHistory(user_id=user.user_id,password_hash=old_hash))
    db.flush()
    stale_history_ids=[
        row.history_id
        for row in db.query(PasswordHistory.history_id)
        .filter_by(user_id=user.user_id)
        .order_by(PasswordHistory.history_id.desc())
        .offset(5)
        .all()
    ]
    if stale_history_ids:
        db.query(PasswordHistory).filter(
            PasswordHistory.history_id.in_(stale_history_ids)
        ).delete(synchronize_session=False)
    record_activity(db,user.user_id,"PASSWORD_CHANGED","USER",user.user_id,{"outcome":"SUCCESS"})
    db.commit()
    return {
        "message":"Password changed successfully",
        "access_token":create_access_token(user.username,user.password_version),
        "token_type":"bearer",
        "user":{"id":user.user_id,"username":user.username,"name":user.full_name,"role":user.role.role_name,"must_change_password":False},
    }
