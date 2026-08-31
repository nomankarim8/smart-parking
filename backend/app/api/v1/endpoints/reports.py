import csv
from io import StringIO
from datetime import datetime, timedelta
from fastapi import APIRouter,Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.all_models import ParkingRecord,Payment,VehicleCategory,Vehicle,ParkingSlot
from app.api.deps import current_user
router=APIRouter()

@router.get("/history.csv")
def csv_export(db:Session=Depends(get_db),_=Depends(current_user)):
    out=StringIO(); w=csv.writer(out); w.writerow(["Parking ID","Plate","Category","Slot","Entry","Exit","Status"])
    for r in db.query(ParkingRecord).order_by(ParkingRecord.record_id.desc()).limit(5000):
        w.writerow([r.record_id,r.vehicle.plate_number,r.vehicle.category.category_name,r.slot.slot_number,r.entry_time,r.exit_time or "",r.status.value])
    out.seek(0); return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=parking_history.csv"})

@router.get("/summary")
def summary(db:Session=Depends(get_db),_=Depends(current_user)):
    now=datetime.utcnow(); start=now.replace(hour=0,minute=0,second=0,microsecond=0)
    entered=db.query(func.count(ParkingRecord.record_id)).filter(ParkingRecord.entry_time>=start).scalar() or 0
    exited=db.query(func.count(ParkingRecord.record_id)).filter(ParkingRecord.exit_time>=start).scalar() or 0
    revenue=db.query(func.coalesce(func.sum(Payment.net_amount),0)).filter(Payment.payment_time>=start,Payment.payment_status=="PAID").scalar() or 0
    bycat=db.query(VehicleCategory.category_name,func.count(ParkingRecord.record_id)).join(Vehicle,Vehicle.category_id==VehicleCategory.category_id).join(ParkingRecord,ParkingRecord.vehicle_id==Vehicle.vehicle_id).filter(ParkingRecord.entry_time>=start).group_by(VehicleCategory.category_name).all()
    return {"date":start.date().isoformat(),"entered":entered,"exited":exited,"revenue":float(revenue),"categories":[{"category":n,"count":int(c)} for n,c in bycat]}
