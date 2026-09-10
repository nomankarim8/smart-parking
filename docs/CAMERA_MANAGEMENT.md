# Camera Management

The system uses three dedicated camera roles:

- `ENTRY` — main entry gate, used for incoming vehicle/ALPR capture.
- `EXIT` — main exit gate, used for exit ALPR, billing and checkout capture.
- `PARKING_ZONE` — parking-area monitoring.

Default demo cameras are seeded as `ENTRY-01`, `EXIT-01`, and `ZONE-A`.

The React Camera Management screen supports add, edit and delete operations for SUPER_ADMIN/ADMIN users. Supported camera types are USB, IP, RTSP, Upload-only and Demo.

For an existing database created before camera roles were added, run `database/migration_camera_roles.sql` once. For a fresh installation, run `schema.sql` then `seeds.sql`.
