from sqlalchemy.orm import Session
from app.models.all_models import Role,VehicleCategory,PricingRule,ParkingSlot,User,Camera,CameraRole,CameraStatus
from app.core.config import settings
from app.core.security import hash_password
from app.services.activity import record_activity

def bootstrap(db:Session):
    roles=[("SUPER_ADMIN","Full access"),("ADMIN","Operational and reporting access"),("OPERATOR","Entry, exit and parking operations"),("VIEWER","Read only access")]
    for i,(name,desc) in enumerate(roles,1):
        if not db.query(Role).filter_by(role_name=name).first(): db.add(Role(role_id=i,role_name=name,description=desc))
    cats=[("MOTORCYCLE","Two-wheeler",20,150),("CAR","Sedan, hatchback and SUV",50,500),("VAN","Microbus and passenger van",80,800),("BUS","Large passenger vehicle",100,1200),("TRUCK","Heavy vehicle",120,1500)]
    db.flush()
    for i,(name,desc,rate,daily) in enumerate(cats,1):
        c=db.query(VehicleCategory).filter_by(category_name=name).first()
        if not c: c=VehicleCategory(category_id=i,category_name=name,description=desc); db.add(c); db.flush()
        if not db.query(PricingRule).filter_by(category_id=c.category_id).first(): db.add(PricingRule(category_id=c.category_id,hourly_rate=rate,min_charge=rate,grace_period_minutes=15,daily_max_charge=daily,overnight_charge=rate*2))
    db.flush()
    slot_seed=[("A",2,5),("B",1,4),("C",3,2),("D",4,1),("E",5,1)]
    for prefix,cat_id,count in slot_seed:
        for n in range(1,count+1):
            if not db.query(ParkingSlot).filter_by(slot_number=f"{prefix}{n:02d}").first(): db.add(ParkingSlot(slot_number=f"{prefix}{n:02d}",category_id=cat_id))
    if not db.query(User).join(Role).filter(
        Role.role_name.in_(("SUPER_ADMIN", "ADMIN"))
    ).first():
        password=settings.INITIAL_ADMIN_PASSWORD
        if len(password)<12:
            raise RuntimeError("Set INITIAL_ADMIN_PASSWORD to a unique password of at least 12 characters before first startup.")
        role=db.query(Role).filter_by(role_name="SUPER_ADMIN").one()
        admin=User(username="admin",email="admin@smartparking.local",full_name="System Administrator",role_id=role.role_id,password_hash=hash_password(password),must_change_password=True)
        db.add(admin)
        db.flush()
        record_activity(db,admin.user_id,"ADMIN_BOOTSTRAPPED","USER",admin.user_id,{"source":"environment_bootstrap","must_change_password":True})
    for name,loc,role in [("ENTRY-01","Main Entry Gate",CameraRole.ENTRY),("EXIT-01","Main Exit Gate",CameraRole.EXIT),("ZONE-A","Parking Zone A",CameraRole.PARKING_ZONE)]:
        cam=db.query(Camera).filter_by(camera_name=name).first()
        if not cam:
            db.add(Camera(camera_name=name,location=loc,camera_role=role,camera_type="DEMO",status=CameraStatus.UNKNOWN))
        else:
            if cam.camera_role is None:
                cam.camera_role=role
            if not cam.stream_url and cam.status == CameraStatus.ONLINE:
                cam.status=CameraStatus.UNKNOWN
    db.commit()
