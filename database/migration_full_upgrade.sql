-- Run this ONLY when upgrading an older copy of the project.
-- For a fresh installation, use schema.sql + seeds.sql instead.
USE smart_parking_db;

-- Camera roles
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

-- Rich Bangla/English ALPR metadata
ALTER TABLE plate_detections
  ADD COLUMN region_name VARCHAR(80) NULL AFTER normalized_plate,
  ADD COLUMN class_bn VARCHAR(20) NULL AFTER region_name,
  ADD COLUMN class_code VARCHAR(20) NULL AFTER class_bn,
  ADD COLUMN series_number VARCHAR(2) NULL AFTER class_code,
  ADD COLUMN vehicle_number VARCHAR(4) NULL AFTER series_number,
  ADD COLUMN ocr_language VARCHAR(20) NULL AFTER vehicle_number,
  ADD COLUMN vehicle_category VARCHAR(50) NULL AFTER ocr_language;

CREATE INDEX idx_plate_detection_class_code ON plate_detections(class_code);
CREATE INDEX idx_plate_detection_region ON plate_detections(region_name);
