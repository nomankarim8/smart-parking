-- MySQL/MariaDB migration. Back up the database before applying.
-- Preflight: this query must return no rows before the ALTER.
SELECT vehicle_id
FROM parking_records
WHERE status = 'PARKED'
GROUP BY vehicle_id
HAVING COUNT(*) > 1;

ALTER TABLE parking_records
  ADD COLUMN active_vehicle_id INT
    GENERATED ALWAYS AS (
      CASE WHEN status = 'PARKED' THEN vehicle_id ELSE NULL END
    ) STORED,
  ADD UNIQUE KEY uq_parking_records_active_vehicle (active_vehicle_id);
