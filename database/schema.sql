CREATE DATABASE IF NOT EXISTS smart_parking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_parking_db;

CREATE TABLE IF NOT EXISTS roles (
  role_id INT AUTO_INCREMENT PRIMARY KEY,
  role_name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  role_id INT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT,
  INDEX idx_users_role (role_id), INDEX idx_users_active (is_active)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS vehicle_categories (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  category_name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS vehicles (
  vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
  plate_number VARCHAR(80) NOT NULL,
  normalized_plate VARCHAR(80) NOT NULL UNIQUE,
  category_id INT NOT NULL,
  owner_name VARCHAR(120), owner_phone VARCHAR(30), owner_email VARCHAR(120),
  address VARCHAR(255), vehicle_model VARCHAR(100), vehicle_color VARCHAR(60),
  registration_info VARCHAR(255), notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_vehicle_category FOREIGN KEY(category_id) REFERENCES vehicle_categories(category_id),
  INDEX idx_vehicle_plate (normalized_plate), INDEX idx_vehicle_category(category_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS parking_slots (
  slot_id INT AUTO_INCREMENT PRIMARY KEY,
  slot_number VARCHAR(20) NOT NULL UNIQUE,
  category_id INT NOT NULL,
  status ENUM('AVAILABLE','OCCUPIED','RESERVED','MAINTENANCE') NOT NULL DEFAULT 'AVAILABLE',
  current_vehicle_id INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_slot_category FOREIGN KEY(category_id) REFERENCES vehicle_categories(category_id),
  CONSTRAINT fk_slot_vehicle FOREIGN KEY(current_vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE SET NULL,
  INDEX idx_slot_status(status), INDEX idx_slot_category(category_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pricing_rules (
  rule_id INT AUTO_INCREMENT PRIMARY KEY,
  category_id INT NOT NULL UNIQUE,
  hourly_rate DECIMAL(10,2) NOT NULL,
  min_charge DECIMAL(10,2) NOT NULL DEFAULT 0,
  grace_period_minutes INT NOT NULL DEFAULT 15,
  daily_max_charge DECIMAL(10,2) NULL,
  overnight_charge DECIMAL(10,2) NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_price_category FOREIGN KEY(category_id) REFERENCES vehicle_categories(category_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cameras (
  camera_id INT AUTO_INCREMENT PRIMARY KEY,
  camera_name VARCHAR(100) NOT NULL UNIQUE,
  location VARCHAR(160) NOT NULL,
  camera_type ENUM('USB','IP','RTSP','UPLOAD','DEMO') NOT NULL DEFAULT 'DEMO',
  stream_url VARCHAR(500),
  status ENUM('ONLINE','OFFLINE','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS parking_records (
  record_id INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id INT NOT NULL, slot_id INT NOT NULL,
  entry_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  exit_time DATETIME NULL,
  entry_image_url VARCHAR(500), exit_image_url VARCHAR(500), plate_image_url VARCHAR(500),
  raw_ocr_text VARCHAR(255), ocr_confidence DECIMAL(5,4),
  status ENUM('PARKED','COMPLETED','CANCELLED') NOT NULL DEFAULT 'PARKED',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_record_vehicle FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id),
  CONSTRAINT fk_record_slot FOREIGN KEY(slot_id) REFERENCES parking_slots(slot_id),
  INDEX idx_record_status_entry(status, entry_time), INDEX idx_record_vehicle(vehicle_id), INDEX idx_record_slot(slot_id), INDEX idx_record_exit(exit_time)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS plate_detections (
  detection_id INT AUTO_INCREMENT PRIMARY KEY,
  camera_id INT NULL, parking_record_id INT NULL,
  detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  raw_text VARCHAR(255), normalized_plate VARCHAR(80), confidence DECIMAL(5,4) NOT NULL DEFAULT 0,
  image_url VARCHAR(500), verification_status ENUM('AUTO_ACCEPTED','MANUAL_REQUIRED','MANUALLY_CORRECTED') NOT NULL DEFAULT 'MANUAL_REQUIRED',
  CONSTRAINT fk_detection_camera FOREIGN KEY(camera_id) REFERENCES cameras(camera_id) ON DELETE SET NULL,
  CONSTRAINT fk_detection_record FOREIGN KEY(parking_record_id) REFERENCES parking_records(record_id) ON DELETE SET NULL,
  INDEX idx_detection_plate(normalized_plate), INDEX idx_detection_time(detected_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS payments (
  payment_id INT AUTO_INCREMENT PRIMARY KEY,
  record_id INT NOT NULL UNIQUE,
  total_duration_minutes INT NOT NULL,
  gross_amount DECIMAL(10,2) NOT NULL, discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0, net_amount DECIMAL(10,2) NOT NULL,
  payment_method ENUM('CASH','CARD','MOBILE_BANKING','ONLINE') NOT NULL,
  payment_status ENUM('PENDING','PAID','FAILED','REFUNDED') NOT NULL DEFAULT 'PENDING',
  transaction_reference VARCHAR(120),
  payment_time DATETIME NULL, created_by INT NULL,
  CONSTRAINT fk_payment_record FOREIGN KEY(record_id) REFERENCES parking_records(record_id),
  CONSTRAINT fk_payment_user FOREIGN KEY(created_by) REFERENCES users(user_id) ON DELETE SET NULL,
  INDEX idx_payment_time(payment_time), INDEX idx_payment_status(payment_status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS blacklist (
  blacklist_id INT AUTO_INCREMENT PRIMARY KEY,
  plate_number VARCHAR(80) NOT NULL UNIQUE, reason VARCHAR(255) NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE,
  added_by INT NOT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, notes TEXT,
  CONSTRAINT fk_blacklist_user FOREIGN KEY(added_by) REFERENCES users(user_id),
  INDEX idx_blacklist_active(is_active), INDEX idx_blacklist_plate(plate_number)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  notification_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(150) NOT NULL, message VARCHAR(500) NOT NULL, severity ENUM('INFO','WARNING','CRITICAL') NOT NULL DEFAULT 'INFO',
  is_read BOOLEAN NOT NULL DEFAULT FALSE, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by INT NULL,
  CONSTRAINT fk_notification_user FOREIGN KEY(created_by) REFERENCES users(user_id) ON DELETE SET NULL,
  INDEX idx_notification_created(created_at), INDEX idx_notification_unread(is_read)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS activity_logs (
  log_id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NULL, action VARCHAR(120) NOT NULL, entity_type VARCHAR(80), entity_id INT NULL, details JSON NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_log_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE SET NULL, INDEX idx_log_time(created_at), INDEX idx_log_action(action)
) ENGINE=InnoDB;
