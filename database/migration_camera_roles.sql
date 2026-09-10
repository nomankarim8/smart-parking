USE smart_parking_db;

ALTER TABLE cameras
  ADD COLUMN camera_role ENUM('ENTRY','EXIT','PARKING_ZONE') NOT NULL DEFAULT 'PARKING_ZONE' AFTER location;

UPDATE cameras SET camera_role='ENTRY' WHERE camera_name='ENTRY-01';
UPDATE cameras SET camera_role='EXIT' WHERE camera_name='EXIT-01';
UPDATE cameras SET camera_role='PARKING_ZONE' WHERE camera_name='ZONE-A';

INSERT IGNORE INTO cameras(camera_name,location,camera_role,camera_type,status)
VALUES
('ENTRY-01','Main Entry Gate','ENTRY','DEMO','ONLINE'),
('EXIT-01','Main Exit Gate','EXIT','DEMO','ONLINE'),
('ZONE-A','Parking Zone A','PARKING_ZONE','DEMO','ONLINE');
