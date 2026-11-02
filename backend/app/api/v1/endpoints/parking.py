from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models.all_models import Vehicle,ParkingSlot,SlotStatus,ParkingRecord,ParkingStatus,Payment,PaymentMethod,PaymentStatus,Notification,Camera,CameraRole,PlateDetection
from app.services.plate import normalize, parse_plate
from app.services.blacklist import active_blacklist_entry
from app.services.billing import calculate
from app.schemas.models import EntryIn,EntryOut,ExitIn,ExitOut
from app.api.deps import current_user,require_roles
from app.services.activity import create_notification,record_activity
router=APIRouter()

def _raise_entry_conflict(db:Session,plate:str,exc:IntegrityError)->None:
    db.rollback()
    existing_vehicle=db.query(Vehicle).filter_by(normalized_plate=plate).first()
    if existing_vehicle and db.query(ParkingRecord).filter_by(
        vehicle_id=existing_vehicle.vehicle_id,
        status=ParkingStatus.PARKED,
    ).first():
        raise HTTPException(409,"Vehicle already has an active parking session") from exc
    raise HTTPException(409,"Vehicle or parking slot changed during entry; retry the operation.") from exc

@router.post("/entry",response_model=EntryOut)
def entry(payload:EntryIn,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN","OPERATOR"))):
    if payload.camera_id:
        camera=db.get(Camera,payload.camera_id)
        if not camera: raise HTTPException(404,"Entry camera not found")
        if camera.camera_role != CameraRole.ENTRY: raise HTTPException(400,"Selected camera is not configured as an ENTRY camera")
    source_text = payload.raw_ocr_text or payload.license_plate
    parsed = parse_plate(source_text)
    if payload.ocr_confidence is not None and (
        payload.ocr_confidence < 0.80 or not parsed.get("valid")
    ):
        raise HTTPException(
            409,
            "Plate recognition requires manual verification before vehicle entry.",
        )
    plate = parsed["normalized_plate"] or normalize(payload.license_plate)
    resolved_category_id = parsed.get("suggested_category_id") or payload.category_id
    blacklist_entry = active_blacklist_entry(db, plate)
    if blacklist_entry:
        create_notification(
            db,
            "Blacklisted Vehicle Entry Blocked",
            f"Entry was denied for blacklisted plate {plate}.",
            "CRITICAL",
            user.user_id,
        )
        record_activity(
            db,
            user.user_id,
            "BLACKLIST_ENTRY_BLOCKED",
            "BLACKLIST",
            blacklist_entry.blacklist_id,
            {"plate_number": plate, "outcome": "BLOCKED"},
        )
        db.commit()
        raise HTTPException(409, "Vehicle is on the active blacklist; entry is denied.")
    vehicle=db.query(Vehicle).filter_by(normalized_plate=plate).first()
    if not vehicle:
        vehicle=Vehicle(plate_number=plate,normalized_plate=plate,category_id=resolved_category_id); db.add(vehicle)
        try:
            db.flush()
        except IntegrityError as exc:
            _raise_entry_conflict(db,plate,exc)
    elif parsed.get("suggested_category_id") and vehicle.category_id != parsed["suggested_category_id"]:
        # Do not silently overwrite a registered vehicle category. Keep the database authoritative.
        resolved_category_id = vehicle.category_id
    active=db.query(ParkingRecord).filter_by(vehicle_id=vehicle.vehicle_id,status=ParkingStatus.PARKED).first()
    if active: raise HTTPException(409,"Vehicle already has an active parking session")
    slot=db.query(ParkingSlot).filter(ParkingSlot.category_id==vehicle.category_id,ParkingSlot.status==SlotStatus.AVAILABLE).order_by(ParkingSlot.slot_number).with_for_update().first()
    if not slot: raise HTTPException(409,"Parking Full - No Available Slot for this category")
    slot.status=SlotStatus.OCCUPIED; slot.current_vehicle_id=vehicle.vehicle_id
    record=ParkingRecord(vehicle_id=vehicle.vehicle_id,slot_id=slot.slot_id,entry_time=datetime.utcnow(),raw_ocr_text=payload.raw_ocr_text,ocr_confidence=payload.ocr_confidence,entry_image_url=payload.entry_image_url,plate_image_url=payload.plate_image_url); db.add(record)
    try:
        db.flush()
    except IntegrityError as exc:
        _raise_entry_conflict(db,plate,exc)
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
    create_notification(db,"Parking session started",f"{plate} entered and was assigned slot {slot.slot_number}.","INFO",user.user_id)
    record_activity(db,user.user_id,"PARKING_SESSION_STARTED","PARKING_RECORD",record.record_id,{"plate_number":plate,"slot":slot.slot_number,"blacklist_alert":False})
    try:
        db.commit()
    except IntegrityError as exc:
        _raise_entry_conflict(db,plate,exc)
    db.refresh(record)
    return {"record_id":record.record_id,"license_plate":vehicle.plate_number,"slot":slot.slot_number,"entry_time":record.entry_time,"status":record.status.value,"blacklist_alert":False}
@router.post("/exit",response_model=ExitOut)
def exit_vehicle(payload:ExitIn,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN","OPERATOR"))):
    try:
        payment_method = PaymentMethod(payload.payment_method.upper())
    except ValueError as exc:
        raise HTTPException(422, "Unsupported payment method") from exc
    if payload.camera_id:
        camera=db.get(Camera,payload.camera_id)
        if not camera: raise HTTPException(404,"Exit camera not found")
        if camera.camera_role != CameraRole.EXIT: raise HTTPException(400,"Selected camera is not configured as an EXIT camera")
    plate=normalize(payload.license_plate); vehicle=db.query(Vehicle).filter_by(normalized_plate=plate).first()
    if not vehicle: raise HTTPException(404,"Vehicle not found")
    record=db.query(ParkingRecord).filter_by(vehicle_id=vehicle.vehicle_id,status=ParkingStatus.PARKED).with_for_update().first()
    if not record: raise HTTPException(404,"Active parking record not found")
    if db.query(Payment).filter_by(record_id=record.record_id).first():
        raise HTTPException(409,"An exit payment is already pending for this parking session.")
    exit_time=datetime.utcnow(); details=calculate(db,vehicle.category_id,record.entry_time,exit_time); discount=max(0,float(payload.discount)); net=max(0,details["amount"]-discount)
    if discount > details["amount"]:
        raise HTTPException(422, "Discount cannot exceed the parking fee.")
    record.exit_time=exit_time; record.exit_image_url=payload.exit_image_url
    if payload.camera_id:
        db.add(PlateDetection(camera_id=payload.camera_id,parking_record_id=record.record_id,normalized_plate=plate,confidence=0,image_url=payload.exit_image_url,verification_status="MANUAL_REQUIRED"))
    no_charge=net<=0
    slot=db.query(ParkingSlot).filter_by(slot_id=record.slot_id).with_for_update().one()
    if slot.current_vehicle_id != vehicle.vehicle_id or slot.status != SlotStatus.OCCUPIED:
        raise HTTPException(409,"Parking slot state conflicts with the active session; ask an administrator to review it.")
    if no_charge:
        record.status=ParkingStatus.COMPLETED
        slot.status=SlotStatus.AVAILABLE
        slot.current_vehicle_id=None
    pm=Payment(record_id=record.record_id,total_duration_minutes=details["minutes"],gross_amount=details["amount"],discount_amount=discount,net_amount=net,payment_method=payment_method,payment_status=PaymentStatus.PAID if no_charge else PaymentStatus.PENDING,payment_time=exit_time if no_charge else None,transaction_reference="NO_CHARGE" if no_charge else None,created_by=user.user_id); db.add(pm)
    create_notification(db,"Parking exit pending payment" if not no_charge else "Parking session ended",f"{vehicle.plate_number} "+("exited from" if no_charge else "is awaiting payment for") + f" slot {slot.slot_number}. "+("No payment was due." if no_charge else f"A payment of ৳{net:.2f} is due; the slot remains occupied until payment is confirmed."),"INFO" if no_charge else "WARNING",user.user_id)
    if not no_charge:
        create_notification(db,"Payment due",f"৳{net:.2f} is due for parking record #{record.record_id} ({vehicle.plate_number}).","WARNING",user.user_id)
    record_activity(db,user.user_id,"PARKING_SESSION_ENDED","PARKING_RECORD",record.record_id,{"plate_number":vehicle.plate_number,"slot":slot.slot_number,"payment_due":net})
    db.commit()
    return {"record_id":record.record_id,"license_plate":vehicle.plate_number,"slot":slot.slot_number,"entry_time":record.entry_time,"exit_time":exit_time,"duration_minutes":details["minutes"],"gross_amount":details["amount"],"discount_amount":discount,"net_amount":net,"payment_status":pm.payment_status.value,"payment_method":payment_method.value}
@router.get("/active")
def active(db:Session=Depends(get_db),_=Depends(current_user)):
    records=db.query(ParkingRecord).filter_by(status=ParkingStatus.PARKED).order_by(ParkingRecord.entry_time.desc()).all(); return [{"record_id":r.record_id,"plate":r.vehicle.plate_number,"slot":r.slot.slot_number,"category":r.vehicle.category.category_name,"entry_time":r.entry_time.isoformat()} for r in records]
@router.get("/history")
def history(db:Session=Depends(get_db),_=Depends(current_user)):
    records=db.query(ParkingRecord).order_by(ParkingRecord.record_id.desc()).limit(500).all(); return [{"record_id":r.record_id,"plate":r.vehicle.plate_number,"slot":r.slot.slot_number,"category":r.vehicle.category.category_name,"entry_time":r.entry_time.isoformat(),"exit_time":r.exit_time.isoformat() if r.exit_time else None,"status":r.status.value} for r in records]
