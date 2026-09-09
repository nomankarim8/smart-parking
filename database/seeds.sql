INSERT IGNORE INTO cameras
(
    camera_name,
    location,
    camera_role,
    camera_type,
    status
)
VALUES
(
    'ENTRY-01',
    'Main Entry Gate',
    'ENTRY',
    'DEMO',
    'ONLINE'
),
(
    'EXIT-01',
    'Main Exit Gate',
    'EXIT',
    'DEMO',
    'ONLINE'
),
(
    'ZONE-A',
    'Parking Zone A',
    'PARKING_ZONE',
    'DEMO',
    'ONLINE'
);