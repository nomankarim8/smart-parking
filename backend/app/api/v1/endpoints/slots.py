from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import ParkingSlot
from app.api.deps import current_user
from app.services.reservations import expire_reservations
router=APIRouter()
@router.get("/")
def slots(
    page:int=Query(default=1,ge=1),
    page_size:int=Query(default=100,ge=1,le=200),
    paginated:bool=False,
    db:Session=Depends(get_db),
    _=Depends(current_user),
):
    expire_reservations(db)
    db.commit()
    query=db.query(ParkingSlot).order_by(ParkingSlot.slot_number)
    items=[{"slot_id":s.slot_id,"slot_number":s.slot_number,"category_id":s.category_id,"category":s.category.category_name,"status":s.status.value,"current_vehicle_id":s.current_vehicle_id} for s in (query.offset((page-1)*page_size).limit(page_size).all() if paginated else query.all())]
    if paginated:
        total=query.count()
        return {"items":items,"total":total,"page":page,"page_size":page_size,"total_pages":(total+page_size-1)//page_size}
    return items
