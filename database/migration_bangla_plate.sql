USE smart_parking_db;

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
