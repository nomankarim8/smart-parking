from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import Vehicle
from app.schemas.models import VehicleIn,VehicleOut
from app.api.deps import current_user,require_roles
from app.services.plate import normalize
from app.services.activity import record_activity
router=APIRouter()
@router.get("/",response_model=list[VehicleOut])
def list_vehicles(q:str|None=None,db:Session=Depends(get_db),_=Depends(current_user)):
    query=db.query(Vehicle).order_by(Vehicle.vehicle_id.desc())
    if q: query=query.filter(Vehicle.normalized_plate.contains(normalize(q)))
    return query.limit(200).all()
@router.post("/",response_model=VehicleOut)
def create_vehicle(payload:VehicleIn,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN","OPERATOR"))):
    n=normalize(payload.plate_number); existing=db.query(Vehicle).filter_by(normalized_plate=n).first()
    if existing: raise HTTPException(409,"Vehicle already exists")
    v=Vehicle(normalized_plate=n,**payload.model_dump()); db.add(v); db.flush(); record_activity(db,_.user_id,"VEHICLE_CREATED","VEHICLE",v.vehicle_id,{"plate_number":v.plate_number,"category_id":v.category_id}); db.commit(); db.refresh(v); return v
@router.put("/{vehicle_id}",response_model=VehicleOut)
def update_vehicle(vehicle_id:int,payload:VehicleIn,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    v=db.get(Vehicle,vehicle_id)
    if not v: raise HTTPException(404,"Vehicle not found")
    before={"plate_number":v.plate_number,"category_id":v.category_id}
    for k,val in payload.model_dump().items(): setattr(v,k,val)
    v.normalized_plate=normalize(v.plate_number); record_activity(db,_.user_id,"VEHICLE_UPDATED","VEHICLE",v.vehicle_id,{"before":before,"after":{"plate_number":v.plate_number,"category_id":v.category_id}}); db.commit(); db.refresh(v); return v
@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id:int,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    v=db.get(Vehicle,vehicle_id)
    if not v: raise HTTPException(404,"Vehicle not found")
    details={"plate_number":v.plate_number,"category_id":v.category_id}; vehicle_id=v.vehicle_id; db.delete(v); record_activity(db,_.user_id,"VEHICLE_DELETED","VEHICLE",vehicle_id,details); db.commit(); return {"ok":True}
