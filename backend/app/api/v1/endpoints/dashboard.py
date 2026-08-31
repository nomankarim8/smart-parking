from datetime import datetime,date
from sqlalchemy import func
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import ParkingSlot,SlotStatus,ParkingRecord,ParkingStatus,Payment,PaymentStatus,VehicleCategory
from app.api.deps import current_user
router=APIRouter()
@router.get("/stats")
def stats(db:Session=Depends(get_db),_=Depends(current_user)):
    total=db.query(ParkingSlot).count(); available=db.query(ParkingSlot).filter_by(status=SlotStatus.AVAILABLE).count(); occupied=db.query(ParkingSlot).filter_by(status=SlotStatus.OCCUPIED).count(); today_start=datetime.combine(date.today(),datetime.min.time()); vehicles_today=db.query(ParkingRecord).filter(ParkingRecord.entry_time>=today_start).count(); parked=db.query(ParkingRecord).filter_by(status=ParkingStatus.PARKED).count(); revenue=db.query(func.coalesce(func.sum(Payment.net_amount),0)).filter(Payment.payment_status==PaymentStatus.PAID,Payment.payment_time>=today_start).scalar();
    cats=db.query(VehicleCategory).all(); breakdown=[]
    for c in cats:
        breakdown.append({"category":c.category_name,"count":db.query(ParkingRecord).join(ParkingRecord.vehicle).filter(ParkingRecord.entry_time>=today_start,ParkingRecord.vehicle.has(category_id=c.category_id)).count()})
    return {"total_slots":total,"available_slots":available,"occupied_slots":occupied,"today_vehicles":vehicles_today,"currently_parked":parked,"today_revenue":float(revenue or 0),"occupancy":round((occupied/total*100) if total else 0,1),"category_breakdown":breakdown}
