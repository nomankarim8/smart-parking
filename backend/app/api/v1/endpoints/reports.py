import csv
from io import StringIO
from datetime import date
from fastapi import APIRouter,Depends,HTTPException,Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.all_models import ParkingRecord,Payment,PaymentStatus,ParkingStatus,VehicleCategory,Vehicle,ParkingSlot
from app.api.deps import current_user
from app.services.reporting import reporting_window
router=APIRouter()

def safe_csv_cell(value):
    if not isinstance(value, str):
        return value
    if value.lstrip(" \t\r\n")[:1] in {"=", "+", "-", "@"} or value[:1] in {"\t", "\r", "\n"}:
        return "'" + value
    return value

def history_query(db,start_date,end_date,plate,category_id,payment_status,session_status):
    range_start,range_end,utc_start,utc_end=reporting_window(start_date,end_date)
    query=db.query(ParkingRecord).join(ParkingRecord.vehicle).join(Vehicle.category).join(ParkingRecord.slot).outerjoin(Payment)
    query=query.filter(ParkingRecord.entry_time>=utc_start,ParkingRecord.entry_time<utc_end)
    if plate:
        normalized=plate.strip().upper()
        if normalized:
            query=query.filter(Vehicle.normalized_plate.contains(normalized,autoescape=True))
    if category_id is not None:
        query=query.filter(Vehicle.category_id==category_id)
    if payment_status:
        try:
            query=query.filter(Payment.payment_status==PaymentStatus(payment_status.upper()))
        except ValueError as exc:
            raise HTTPException(422,"Unsupported payment status filter") from exc
    if session_status:
        try:
            query=query.filter(ParkingRecord.status==ParkingStatus(session_status.upper()))
        except ValueError as exc:
            raise HTTPException(422,"Unsupported session status filter") from exc
    return range_start,range_end,query

@router.get("/history")
def history(
    start_date:date|None=None,
    end_date:date|None=None,
    plate:str|None=Query(default=None,max_length=80),
    category_id:int|None=Query(default=None,ge=1),
    payment_status:str|None=None,
    session_status:str|None=None,
    page:int=Query(default=1,ge=1),
    page_size:int=Query(default=50,ge=1,le=200),
    db:Session=Depends(get_db),
    _=Depends(current_user),
):
    range_start,range_end,query=history_query(db,start_date,end_date,plate,category_id,payment_status,session_status)
    total=query.count()
    rows=query.add_columns(Payment.payment_status).order_by(ParkingRecord.record_id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {
        "start_date":range_start.isoformat(),
        "end_date":range_end.isoformat(),
        "total":total,
        "page":page,
        "page_size":page_size,
        "items":[
            {
                "record_id":row.record_id,
                "plate":row.vehicle.normalized_plate,
                "category":row.vehicle.category.category_name,
                "slot":row.slot.slot_number,
                "entry_time":row.entry_time.isoformat(),
                "exit_time":row.exit_time.isoformat() if row.exit_time else None,
                "status":row.status.value,
                "payment_status":payment_status.value if payment_status else None,
            }
            for row,payment_status in rows
        ],
    }

@router.get("/history.csv")
def csv_export(
    start_date:date|None=None,
    end_date:date|None=None,
    plate:str|None=Query(default=None,max_length=80),
    category_id:int|None=Query(default=None,ge=1),
    payment_status:str|None=None,
    session_status:str|None=None,
    db:Session=Depends(get_db),
    _=Depends(current_user),
):
    _,_,query=history_query(db,start_date,end_date,plate,category_id,payment_status,session_status)
    out=StringIO(); w=csv.writer(out); w.writerow(["Parking ID","Plate","Category","Slot","Entry","Exit","Status","Payment status"])
    records=query.add_columns(Payment.payment_status).order_by(ParkingRecord.record_id.desc()).limit(5000)
    for r,payment_status in records:
        w.writerow([safe_csv_cell(v) for v in [r.record_id,r.vehicle.plate_number,r.vehicle.category.category_name,r.slot.slot_number,r.entry_time,r.exit_time or "",r.status.value,payment_status.value if payment_status else ""]])
    out.seek(0); return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=parking_history.csv"})

@router.get("/summary")
def summary(start_date:date|None=None,end_date:date|None=None,db:Session=Depends(get_db),_=Depends(current_user)):
    range_start,range_end,utc_start,utc_end=reporting_window(start_date,end_date)
    entered=db.query(func.count(ParkingRecord.record_id)).filter(ParkingRecord.entry_time>=utc_start,ParkingRecord.entry_time<utc_end).scalar() or 0
    exited=db.query(func.count(ParkingRecord.record_id)).filter(ParkingRecord.exit_time>=utc_start,ParkingRecord.exit_time<utc_end).scalar() or 0
    revenue=db.query(func.coalesce(func.sum(Payment.net_amount),0)).filter(Payment.payment_time>=utc_start,Payment.payment_time<utc_end,Payment.payment_status=="PAID").scalar() or 0
    bycat=db.query(VehicleCategory.category_name,func.count(ParkingRecord.record_id)).join(Vehicle,Vehicle.category_id==VehicleCategory.category_id).join(ParkingRecord,ParkingRecord.vehicle_id==Vehicle.vehicle_id).filter(ParkingRecord.entry_time>=utc_start,ParkingRecord.entry_time<utc_end).group_by(VehicleCategory.category_name).all()
    return {"start_date":range_start.isoformat(),"end_date":range_end.isoformat(),"entered":entered,"exited":exited,"revenue":float(revenue),"categories":[{"category":n,"count":int(c)} for n,c in bycat]}
