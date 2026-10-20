from datetime import datetime,date,timedelta
from sqlalchemy import func
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import ParkingSlot,SlotStatus,ParkingRecord,ParkingStatus,Payment,PaymentStatus,VehicleCategory,Notification
from app.api.deps import current_user
from app.services.reservations import expire_reservations
router=APIRouter()
@router.get("/stats")
def stats(db:Session=Depends(get_db),_=Depends(current_user)):
    expire_reservations(db)
    db.commit()
    total=db.query(ParkingSlot).count(); available=db.query(ParkingSlot).filter_by(status=SlotStatus.AVAILABLE).count(); occupied=db.query(ParkingSlot).filter_by(status=SlotStatus.OCCUPIED).count(); reserved=db.query(ParkingSlot).filter_by(status=SlotStatus.RESERVED).count(); today_start=datetime.combine(date.today(),datetime.min.time()); vehicles_today=db.query(ParkingRecord).filter(ParkingRecord.entry_time>=today_start).count(); parked=db.query(ParkingRecord).filter_by(status=ParkingStatus.PARKED).count(); revenue=db.query(func.coalesce(func.sum(Payment.net_amount),0)).filter(Payment.payment_status==PaymentStatus.PAID,Payment.payment_time>=today_start).scalar(); unread_notifications=db.query(Notification).filter_by(is_read=False).count(); payments_due=db.query(Payment).filter(Payment.payment_status.in_([PaymentStatus.PENDING,PaymentStatus.FAILED])).count()
    cats=db.query(VehicleCategory).all(); breakdown=[]
    for c in cats:
        breakdown.append({"category":c.category_name,"count":db.query(ParkingRecord).join(ParkingRecord.vehicle).filter(ParkingRecord.entry_time>=today_start,ParkingRecord.vehicle.has(category_id=c.category_id)).count()})
    return {"total_slots":total,"available_slots":available,"occupied_slots":occupied,"reserved_slots":reserved,"today_vehicles":vehicles_today,"currently_parked":parked,"today_revenue":float(revenue or 0),"occupancy":round((occupied/total*100) if total else 0,1),"category_breakdown":breakdown,"unread_notifications":unread_notifications,"payments_due":payments_due}

@router.get("/forecast")
def forecast(hours:int=24,db:Session=Depends(get_db),_=Depends(current_user)):
    if hours < 1 or hours > 48:
        from fastapi import HTTPException
        raise HTTPException(400,"hours must be between 1 and 48")
    now=datetime.utcnow()
    window_start=(now-timedelta(days=56)).replace(minute=0,second=0,microsecond=0)
    window_end=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
    records=db.query(ParkingRecord.entry_time,ParkingRecord.exit_time).filter(
        ParkingRecord.entry_time < window_end,
        (ParkingRecord.exit_time.is_(None)) | (ParkingRecord.exit_time > window_start),
    ).all()
    total_slots=db.query(ParkingSlot).count()
    hourly_deltas={}
    arrival_counts={}
    for entry_time,exit_time in records:
        if entry_time >= window_start:
            arrival_key=entry_time.replace(minute=0,second=0,microsecond=0)
            arrival_counts[arrival_key]=arrival_counts.get(arrival_key,0)+1
        start=max(entry_time,window_start)
        finish=min(exit_time or now,window_end)
        start_index=max(0,int((start-window_start).total_seconds()//3600))
        if start.minute or start.second or start.microsecond:
            start_index+=1
        finish_index=max(0,int((finish-window_start).total_seconds()//3600))
        if finish.minute or finish.second or finish.microsecond:
            finish_index+=1
        if start_index < finish_index:
            hourly_deltas[start_index]=hourly_deltas.get(start_index,0)+1
            hourly_deltas[finish_index]=hourly_deltas.get(finish_index,0)-1

    observed={}
    occupied=0
    for index in range(int((window_end-window_start).total_seconds()//3600)+1):
        occupied+=hourly_deltas.get(index,0)
        bucket=window_start+timedelta(hours=index)
        observed.setdefault((bucket.weekday(),bucket.hour),[]).append(max(0,occupied))

    forecast_start=window_end
    periods=[]
    for offset in range(hours):
        bucket=forecast_start+timedelta(hours=offset)
        samples=observed.get((bucket.weekday(),bucket.hour),[])
        predicted_occupied=sum(samples)/len(samples) if samples else 0.0
        occupancy_percent=min(100.0,(predicted_occupied/total_slots*100)) if total_slots else 0.0
        demand="HIGH" if occupancy_percent>=75 else "MODERATE" if occupancy_percent>=40 else "LOW"
        arrival_samples=[
            arrival_counts.get(window_start+timedelta(hours=index),0)
            for index in range(int((window_end-window_start).total_seconds()//3600))
            if (window_start+timedelta(hours=index)).weekday()==bucket.weekday()
            and (window_start+timedelta(hours=index)).hour==bucket.hour
        ]
        periods.append({
            "hour":bucket.isoformat()+"Z",
            "expected_arrivals":round(sum(arrival_samples)/len(arrival_samples),1) if arrival_samples else 0.0,
            "expected_occupied_slots":round(predicted_occupied,1),
            "expected_occupancy_percent":round(occupancy_percent,1),
            "demand":demand,
            "sample_weeks":len(samples),
        })
    return {
        "based_on_days":56,
        "total_slots":total_slots,
        "current_occupied":db.query(ParkingSlot).filter_by(status=SlotStatus.OCCUPIED).count(),
        "forecast":periods,
    }
