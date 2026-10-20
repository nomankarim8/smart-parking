from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter,UploadFile,File,Depends,HTTPException,Query
from app.services.alpr import alpr_service
from app.schemas.models import ALPRResponse
from app.api.deps import current_user

router=APIRouter()
UPLOAD_DIR=Path(__file__).resolve().parents[3]/"uploads"
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)

@router.post("/detect",response_model=ALPRResponse)
async def detect(file:UploadFile=File(...),persist:bool=Query(default=True),_=Depends(current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400,"Please upload an image file")
    data=await file.read()
    if not data:
        raise HTTPException(400,"Uploaded image is empty")
    if len(data)>10*1024*1024:
        raise HTTPException(413,"Image is too large. Maximum size is 10 MB")
    suffix=Path(file.filename or ".jpg").suffix.lower() or ".jpg"
    target=UPLOAD_DIR/f"{uuid4().hex}{suffix}" if persist else None
    if target:
        target.write_bytes(data)
    try:
        result=alpr_service.recognize(data)
    except Exception as exc:
        if target:
            target.unlink(missing_ok=True)
        raise HTTPException(422,f"ALPR processing failed: {exc}")
    result["input_image_url"]=f"/uploads/{target.name}" if target else None
    return result
