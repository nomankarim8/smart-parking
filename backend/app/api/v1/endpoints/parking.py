from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import Vehicle,ParkingSlot,SlotStatus,ParkingRecord,ParkingStatus,Payment,PaymentMethod,PaymentStatus,Blacklist,Notification,Camera,CameraRole,PlateDetection
from app.services.plate import normalize, parse_plate
from app.services.billing import calculate
from app.schemas.models import EntryIn,EntryOut,ExitIn,ExitOut
from app.api.deps import current_user,require_roles
router=APIRouter()
@router.post("/entry",response_model=EntryOut)
def entry(payload:EntryIn,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN","OPERATOR"))):
    if payload.camera_id:
        camera=db.get(Camera,payload.camera_id)
        if not camera: raise HTTPException(404,"Entry camera not found")
        if camera.camera_role != CameraRole.ENTRY: raise HTTPException(400,"Selected camera is not configured as an ENTRY camera")
    source_text = payload.raw_ocr_text or payload.license_plate
    parsed = parse_plate(source_text)
    plate = parsed["normalized_plate"] or normalize(payload.license_plate)
    resolved_category_id = parsed.get("suggested_category_id") or payload.category_id
    black=db.query(Blacklist).filter_by(plate_number=plate,is_active=True).first()
    vehicle=db.query(Vehicle).filter_by(normalized_plate=plate).first()
    if not vehicle:
        vehicle=Vehicle(plate_number=plate,normalized_plate=plate,category_id=resolved_category_id); db.add(vehicle); db.flush()
    elif parsed.get("suggested_category_id") and vehicle.category_id != parsed["suggested_category_id"]:
        # Do not silently overwrite a registered vehicle category. Keep the database authoritative.
        resolved_category_id = vehicle.category_id
    active=db.query(ParkingRecord).filter_by(vehicle_id=vehicle.vehicle_id,status=ParkingStatus.PARKED).first()
    if active: raise HTTPException(409,"Vehicle already has an active parking session")
    slot=db.query(ParkingSlot).filter(ParkingSlot.category_id==vehicle.category_id,ParkingSlot.status==SlotStatus.AVAILABLE).order_by(ParkingSlot.slot_number).with_for_update().first()
    if not slot: raise HTTPException(409,"Parking Full - No Available Slot for this category")
    slot.status=SlotStatus.OCCUPIED; slot.current_vehicle_id=vehicle.vehicle_id
    record=ParkingRecord(vehicle_id=vehicle.vehicle_id,slot_id=slot.slot_id,entry_time=datetime.utcnow(),raw_ocr_text=payload.raw_ocr_text,ocr_confidence=payload.ocr_confidence,entry_image_url=payload.entry_image_url,plate_image_url=payload.plate_image_url); db.add(record); db.flush()
    if payload.camera_id:
        db.add(PlateDetection(
            camera_id=payload.camera_id,
            parking_record_id=record.record_id,
            raw_text=payload.raw_ocr_text,
            normalized_plate=plate,
            region_name=parsed.get("region_name"),
            class_bn=parsed.get("class_bn"),
            class_code=parsed.get("class_code"),
            series_number=parsed.get("series_number"),
            vehicle_number=parsed.get("vehicle_number"),
            ocr_language=None,
            vehicle_category=parsed.get("vehicle_category"),
            confidence=payload.ocr_confidence or 0,
            image_url=payload.plate_image_url,
            verification_status="AUTO_ACCEPTED" if (payload.ocr_confidence or 0) >= 0.80 and parsed.get("valid") else "MANUAL_REQUIRED",
        ))
    if black:
        db.add(Notification(title="Blacklisted Vehicle Detected",message=f"Plate {plate} detected at vehicle entry. Manual staff review required.",severity="WARNING",created_by=user.user_id))
    db.commit(); db.refresh(record)
    return {"record_id":record.record_id,"license_plate":vehicle.plate_number,"slot":slot.slot_number,"entry_time":record.entry_time,"status":record.status.value,"blacklist_alert":bool(black)}
@router.post("/exit",response_model=ExitOut)
def exit_vehicle(payload:ExitIn,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN","OPERATOR"))):
    if payload.camera_id:
        camera=db.get(Camera,payload.camera_id)
        if not camera: raise HTTPException(404,"Exit camera not found")
        if camera.camera_role != CameraRole.EXIT: raise HTTPException(400,"Selected camera is not configured as an EXIT camera")
    plate=normalize(payload.license_plate); vehicle=db.query(Vehicle).filter_by(normalized_plate=plate).first()
    if not vehicle: raise HTTPException(404,"Vehicle not found")
    record=db.query(ParkingRecord).filter_by(vehicle_id=vehicle.vehicle_id,status=ParkingStatus.PARKED).first()
    if not record: raise HTTPException(404,"Active parking record not found")
    exit_time=datetime.utcnow(); details=calculate(db,vehicle.category_id,record.entry_time,exit_time); discount=max(0,float(payload.discount)); net=max(0,details["amount"]-discount)
    record.exit_time=exit_time; record.status=ParkingStatus.COMPLETED; record.exit_image_url=payload.exit_image_url
    if payload.camera_id:
        db.add(PlateDetection(camera_id=payload.camera_id,parking_record_id=record.record_id,normalized_plate=plate,confidence=0,image_url=payload.exit_image_url,verification_status="MANUAL_REQUIRED"))
    slot=db.get(ParkingSlot,record.slot_id); slot.status=SlotStatus.AVAILABLE; slot.current_vehicle_id=None
    pm=Payment(record_id=record.record_id,total_duration_minutes=details["minutes"],gross_amount=details["amount"],discount_amount=discount,net_amount=net,payment_method=PaymentMethod(payload.payment_method),payment_status=PaymentStatus.PAID,payment_time=exit_time,transaction_reference=payload.transaction_reference,created_by=user.user_id); db.add(pm); db.commit()
    return {"record_id":record.record_id,"license_plate":vehicle.plate_number,"slot":slot.slot_number,"entry_time":record.entry_time,"exit_time":exit_time,"duration_minutes":details["minutes"],"gross_amount":details["amount"],"discount_amount":discount,"net_amount":net,"payment_status":"PAID","payment_method":payload.payment_method}
@router.get("/active")
def active(db:Session=Depends(get_db),_=Depends(current_user)):
    records=db.query(ParkingRecord).filter_by(status=ParkingStatus.PARKED).order_by(ParkingRecord.entry_time.desc()).all(); return [{"record_id":r.record_id,"plate":r.vehicle.plate_number,"slot":r.slot.slot_number,"category":r.vehicle.category.category_name,"entry_time":r.entry_time.isoformat()} for r in records]
@router.get("/history")
def history(db:Session=Depends(get_db),_=Depends(current_user)):
    records=db.query(ParkingRecord).order_by(ParkingRecord.record_id.desc()).limit(500).all(); return [{"record_id":r.record_id,"plate":r.vehicle.plate_number,"slot":r.slot.slot_number,"category":r.vehicle.category.category_name,"entry_time":r.entry_time.isoformat(),"exit_time":r.exit_time.isoformat() if r.exit_time else None,"status":r.status.value} for r in records]
