-- Apply once after a protected database backup.
-- Existing ADMIN and SUPER_ADMIN accounts are forced to choose a new password.
ALTER TABLE users
  ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN password_changed_at DATETIME NULL,
  ADD COLUMN password_version INT NOT NULL DEFAULT 0;

UPDATE users AS u
JOIN roles AS r ON r.role_id = u.role_id
SET u.must_change_password = TRUE
WHERE r.role_name IN ('SUPER_ADMIN', 'ADMIN');

CREATE TABLE IF NOT EXISTS password_history (
  history_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL,
  INDEX ix_password_history_user_id (user_id),
  CONSTRAINT fk_password_history_user
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
