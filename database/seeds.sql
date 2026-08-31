USE smart_parking_db;
INSERT IGNORE INTO roles(role_id,role_name,description) VALUES
(1,'SUPER_ADMIN','Full access'),(2,'ADMIN','Operational and reporting access'),(3,'OPERATOR','Entry, exit and parking operations'),(4,'VIEWER','Read only access');
INSERT IGNORE INTO vehicle_categories(category_id,category_name,description) VALUES
(1,'MOTORCYCLE','Two-wheeler'),(2,'CAR','Sedan, hatchback and SUV'),(3,'VAN','Microbus and passenger van'),(4,'BUS','Large passenger vehicle'),(5,'TRUCK','Heavy vehicle');
INSERT IGNORE INTO pricing_rules(category_id,hourly_rate,min_charge,grace_period_minutes,daily_max_charge,overnight_charge) VALUES
(1,20,20,15,150,50),(2,50,50,15,500,100),(3,80,80,15,800,150),(4,100,100,15,1200,200),(5,120,120,15,1500,250);
INSERT IGNORE INTO parking_slots(slot_number,category_id,status) VALUES
('A01',2,'AVAILABLE'),('A02',2,'AVAILABLE'),('A03',2,'AVAILABLE'),('A04',2,'AVAILABLE'),('A05',2,'AVAILABLE'),
('B01',1,'AVAILABLE'),('B02',1,'AVAILABLE'),('B03',1,'AVAILABLE'),('B04',1,'AVAILABLE'),
('C01',3,'AVAILABLE'),('C02',3,'AVAILABLE'),('D01',4,'AVAILABLE'),('D02',5,'AVAILABLE');
INSERT IGNORE INTO cameras(camera_name,location,camera_type,status) VALUES
('ENTRY-01','Main Entry Gate','DEMO','ONLINE'),('EXIT-01','Main Exit Gate','DEMO','ONLINE'),('ZONE-A','Parking Zone A','DEMO','ONLINE');
-- Default password for demo user is set by backend first-start bootstrap; this SQL intentionally does not hard-code passwords.
