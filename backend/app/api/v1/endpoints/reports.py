import csv
from io import StringIO
from datetime import date
from fastapi import APIRouter,Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.all_models import ParkingRecord,Payment,VehicleCategory,Vehicle,ParkingSlot
from app.api.deps import current_user
from app.services.reporting import reporting_window
router=APIRouter()

def safe_csv_cell(value):
    if not isinstance(value, str):
        return value
    if value.lstrip(" \t\r\n")[:1] in {"=", "+", "-", "@"} or value[:1] in {"\t", "\r", "\n"}:
        return "'" + value
    return value

@router.get("/history.csv")
def csv_export(start_date:date|None=None,end_date:date|None=None,db:Session=Depends(get_db),_=Depends(current_user)):
    _,_,utc_start,utc_end=reporting_window(start_date,end_date)
    out=StringIO(); w=csv.writer(out); w.writerow(["Parking ID","Plate","Category","Slot","Entry","Exit","Status"])
    records=db.query(ParkingRecord).filter(ParkingRecord.entry_time>=utc_start,ParkingRecord.entry_time<utc_end).order_by(ParkingRecord.record_id.desc()).limit(5000)
    for r in records:
        w.writerow([safe_csv_cell(v) for v in [r.record_id,r.vehicle.plate_number,r.vehicle.category.category_name,r.slot.slot_number,r.entry_time,r.exit_time or "",r.status.value]])
    out.seek(0); return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=parking_history.csv"})

@router.get("/summary")
def summary(start_date:date|None=None,end_date:date|None=None,db:Session=Depends(get_db),_=Depends(current_user)):
    range_start,range_end,utc_start,utc_end=reporting_window(start_date,end_date)
    entered=db.query(func.count(ParkingRecord.record_id)).filter(ParkingRecord.entry_time>=utc_start,ParkingRecord.entry_time<utc_end).scalar() or 0
    exited=db.query(func.count(ParkingRecord.record_id)).filter(ParkingRecord.exit_time>=utc_start,ParkingRecord.exit_time<utc_end).scalar() or 0
    revenue=db.query(func.coalesce(func.sum(Payment.net_amount),0)).filter(Payment.payment_time>=utc_start,Payment.payment_time<utc_end,Payment.payment_status=="PAID").scalar() or 0
    bycat=db.query(VehicleCategory.category_name,func.count(ParkingRecord.record_id)).join(Vehicle,Vehicle.category_id==VehicleCategory.category_id).join(ParkingRecord,ParkingRecord.vehicle_id==Vehicle.vehicle_id).filter(ParkingRecord.entry_time>=utc_start,ParkingRecord.entry_time<utc_end).group_by(VehicleCategory.category_name).all()
    return {"start_date":range_start.isoformat(),"end_date":range_end.isoformat(),"entered":entered,"exited":exited,"revenue":float(revenue),"categories":[{"category":n,"count":int(c)} for n,c in bycat]}
