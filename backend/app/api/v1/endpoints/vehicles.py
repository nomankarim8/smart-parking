from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import Vehicle, VehicleCategory
from app.schemas.models import VehicleIn,VehicleOut
from app.api.deps import current_user,require_roles
from app.services.plate import normalize
from app.services.blacklist import active_blacklist_entry
from app.services.activity import record_activity
router=APIRouter()
@router.get("/",response_model=None)
def list_vehicles(
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    paginated: bool = False,
    db: Session = Depends(get_db),
    _=Depends(current_user),
):
    query=db.query(Vehicle).order_by(Vehicle.vehicle_id.desc())
    if q: query=query.filter(Vehicle.normalized_plate.contains(normalize(q)))
    if paginated:
        total=query.count()
        items=query.offset((page-1)*page_size).limit(page_size).all()
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    return query.limit(200).all()
@router.get("/categories")
def list_vehicle_categories(db:Session=Depends(get_db),_=Depends(current_user)):
    return [
        {"category_id": category.category_id, "category_name": category.category_name}
        for category in db.query(VehicleCategory).order_by(VehicleCategory.category_id).all()
    ]
@router.post("/",response_model=VehicleOut)
def create_vehicle(payload:VehicleIn,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN","OPERATOR"))):
    if not db.get(VehicleCategory, payload.category_id):
        raise HTTPException(422, "Invalid vehicle category")
    n=normalize(payload.plate_number); existing=db.query(Vehicle).filter_by(normalized_plate=n).first()
    if existing: raise HTTPException(409,"Vehicle already exists")
    if active_blacklist_entry(db,n):
        raise HTTPException(409,"Vehicle is on the active blacklist and cannot be registered")
    v=Vehicle(normalized_plate=n,**payload.model_dump()); db.add(v); db.flush(); record_activity(db,_.user_id,"VEHICLE_CREATED","VEHICLE",v.vehicle_id,{"plate_number":v.plate_number,"category_id":v.category_id}); db.commit(); db.refresh(v); return v
@router.put("/{vehicle_id}",response_model=VehicleOut)
def update_vehicle(vehicle_id:int,payload:VehicleIn,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    v=db.get(Vehicle,vehicle_id)
    if not v: raise HTTPException(404,"Vehicle not found")
    if not db.get(VehicleCategory, payload.category_id):
        raise HTTPException(422, "Invalid vehicle category")
    normalized_plate=normalize(payload.plate_number)
    if normalized_plate != v.normalized_plate and active_blacklist_entry(db,normalized_plate):
        raise HTTPException(409,"Vehicle is on the active blacklist and cannot be assigned")
    before={"plate_number":v.plate_number,"category_id":v.category_id}
    for k,val in payload.model_dump().items(): setattr(v,k,val)
    v.normalized_plate=normalized_plate; record_activity(db,_.user_id,"VEHICLE_UPDATED","VEHICLE",v.vehicle_id,{"before":before,"after":{"plate_number":v.plate_number,"category_id":v.category_id}}); db.commit(); db.refresh(v); return v
@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id:int,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    v=db.get(Vehicle,vehicle_id)
    if not v: raise HTTPException(404,"Vehicle not found")
    details={"plate_number":v.plate_number,"category_id":v.category_id}; vehicle_id=v.vehicle_id; db.delete(v); record_activity(db,_.user_id,"VEHICLE_DELETED","VEHICLE",vehicle_id,details); db.commit(); return {"ok":True}
