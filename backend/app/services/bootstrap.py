from sqlalchemy.orm import Session
from app.models.all_models import Role,VehicleCategory,PricingRule,ParkingSlot,User,Camera
from app.core.security import hash_password

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
    if not db.query(User).filter_by(username="admin").first():
        role=db.query(Role).filter_by(role_name="SUPER_ADMIN").one(); db.add(User(username="admin",email="admin@smartparking.local",full_name="System Administrator",role_id=role.role_id,password_hash=hash_password("Admin@12345")))
    for name,loc in [("ENTRY-01","Main Entry Gate"),("EXIT-01","Main Exit Gate"),("ZONE-A","Parking Zone A")]:
        if not db.query(Camera).filter_by(camera_name=name).first(): db.add(Camera(camera_name=name,location=loc,camera_type="DEMO",status="ONLINE"))
    db.commit()
