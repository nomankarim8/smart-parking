from io import BytesIO
from pathlib import Path
import re
from uuid import uuid4
from fastapi import APIRouter,UploadFile,File,Depends,HTTPException,Query
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from app.services.alpr import alpr_service
from app.schemas.models import ALPRResponse
from app.api.deps import current_user
from app.services.media import media_root

router=APIRouter()
UPLOAD_DIR=media_root()
IMAGE_SUFFIXES={"JPEG":".jpg","PNG":".png","WEBP":".webp","BMP":".bmp"}

@router.post("/detect",response_model=ALPRResponse)
async def detect(file:UploadFile=File(...),persist:bool=Query(default=True),_=Depends(current_user)):
    if file.content_type not in {"image/jpeg","image/png","image/webp","image/bmp"}:
        await file.close()
        raise HTTPException(400,"Please upload an image file")
    data=await file.read(10*1024*1024+1)
    await file.close()
    if not data:
        raise HTTPException(400,"Uploaded image is empty")
    if len(data)>10*1024*1024:
        raise HTTPException(413,"Image is too large. Maximum size is 10 MB")
    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            if image.width * image.height > 50_000_000:
                raise HTTPException(413,"Image dimensions exceed the supported limit")
            image.verify()
        if image_format not in IMAGE_SUFFIXES:
            raise HTTPException(400,"Unsupported image format")
        result=alpr_service.recognize(data)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(400,"Uploaded file is not a valid supported image") from exc
    except Exception as exc:
        raise HTTPException(422,"ALPR processing failed. The image could not be processed.") from exc

    target=None
    if persist:
        UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
        target=UPLOAD_DIR/f"{uuid4().hex}{IMAGE_SUFFIXES[image_format]}"
        target.write_bytes(data)
    result["input_image_url"]=f"/api/v1/alpr/media/{target.name}" if target else None
    return result


@router.get("/media/{media_name}")
def get_alpr_media(media_name: str, _=Depends(current_user)):
    if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp|bmp)",media_name):
        raise HTTPException(404,"Media not found")
    root=UPLOAD_DIR.resolve()
    target=(root/media_name).resolve()
    if target.parent!=root or not target.is_file():
        raise HTTPException(404,"Media not found")
    return FileResponse(
        target,
        media_type={"jpg":"image/jpeg","png":"image/png","webp":"image/webp","bmp":"image/bmp"}[target.suffix[1:]],
        headers={"Cache-Control":"private, no-store"},
    )


@router.get("/status")
def alpr_status(_=Depends(current_user)):
    return alpr_service.status()
