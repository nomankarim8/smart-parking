from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import ParkingSlot
from app.api.deps import current_user
router=APIRouter()
@router.get("/")
def slots(db:Session=Depends(get_db),_=Depends(current_user)):
    return [{"slot_id":s.slot_id,"slot_number":s.slot_number,"category_id":s.category_id,"category":s.category.category_name,"status":s.status.value,"current_vehicle_id":s.current_vehicle_id} for s in db.query(ParkingSlot).order_by(ParkingSlot.slot_number).all()]
