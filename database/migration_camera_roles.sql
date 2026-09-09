USE smart_parking_db;

-- 1. Add a functional role for each camera.
-- ENTRY      = Main vehicle entry gate
-- EXIT       = Main vehicle exit gate
-- PARKING_ZONE = Parking-area monitoring

ALTER TABLE cameras
ADD COLUMN camera_role ENUM(
    'ENTRY',
    'EXIT',
    'PARKING_ZONE'
) NOT NULL DEFAULT 'PARKING_ZONE'
AFTER location;

-- 2. Useful index for quick lookup
CREATE INDEX idx_cameras_role ON cameras(camera_role);

-- 3. Update existing/default cameras
UPDATE cameras
SET camera_role = 'ENTRY'
WHERE camera_name = 'ENTRY-01';

UPDATE cameras
SET camera_role = 'EXIT'
WHERE camera_name = 'EXIT-01';

UPDATE cameras
SET camera_role = 'PARKING_ZONE'
WHERE camera_name = 'ZONE-A';

-- 4. Ensure the three required cameras exist
INSERT INTO cameras
(
    camera_name,
    location,
    camera_role,
    camera_type,
    stream_url,
    status
)
SELECT
    'ENTRY-01',
    'Main Entry Gate',
    'ENTRY',
    'DEMO',
    NULL,
    'ONLINE'
WHERE NOT EXISTS (
    SELECT 1
    FROM cameras
    WHERE camera_name = 'ENTRY-01'
);

INSERT INTO cameras
(
    camera_name,
    location,
    camera_role,
    camera_type,
    stream_url,
    status
)
SELECT
    'EXIT-01',
    'Main Exit Gate',
    'EXIT',
    'DEMO',
    NULL,
    'ONLINE'
WHERE NOT EXISTS (
    SELECT 1
    FROM cameras
    WHERE camera_name = 'EXIT-01'
);

INSERT INTO cameras
(
    camera_name,
    location,
    camera_role,
    camera_type,
    stream_url,
    status
)
SELECT
    'ZONE-A',
    'Parking Zone A',
    'PARKING_ZONE',
    'DEMO',
    NULL,
    'ONLINE'
WHERE NOT EXISTS (
    SELECT 1
    FROM cameras
    WHERE camera_name = 'ZONE-A'
);

-- 5. Verify
SELECT
    camera_id,
    camera_name,
    location,
    camera_role,
    camera_type,
    status
FROM cameras
ORDER BY camera_id;