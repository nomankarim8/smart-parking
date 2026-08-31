from fastapi import APIRouter,Depends
from app.api.deps import require_roles
router=APIRouter()
@router.get("/")
def system_settings(_=Depends(require_roles("SUPER_ADMIN","ADMIN"))): return {"currency":"BDT","timezone":"Asia/Dhaka","alpr_confidence_threshold":0.80,"mode":"LIVE+DEMO"}
