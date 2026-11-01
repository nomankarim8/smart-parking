CREATE TABLE IF NOT EXISTS wallet_payment_submissions (
  submission_id INT AUTO_INCREMENT PRIMARY KEY,
  payment_id INT NOT NULL,
  method VARCHAR(20) NOT NULL,
  transaction_id VARCHAR(120) NOT NULL UNIQUE,
  submitted_amount DECIMAL(10,2) NOT NULL,
  payer_wallet_masked VARCHAR(32) NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'PENDING_VERIFICATION',
  submitted_by INT NOT NULL,
  submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  verified_by INT NULL,
  verified_at DATETIME NULL,
  verification_note VARCHAR(500) NULL,
  CONSTRAINT fk_wallet_submission_payment FOREIGN KEY(payment_id) REFERENCES payments(payment_id) ON DELETE CASCADE,
  CONSTRAINT fk_wallet_submission_actor FOREIGN KEY(submitted_by) REFERENCES users(user_id),
  CONSTRAINT fk_wallet_submission_verifier FOREIGN KEY(verified_by) REFERENCES users(user_id) ON DELETE SET NULL,
  INDEX idx_wallet_submission_queue(status, submitted_at),
  INDEX idx_wallet_submission_payment(payment_id)
) ENGINE=InnoDB;
