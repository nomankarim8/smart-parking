from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=1800, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def migrate_admin_password_rotation(bind=engine):
    inspector = inspect(bind)
    if not inspector.has_table("users"):
        return
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    rotation_columns = {
        "must_change_password": "BOOLEAN NOT NULL DEFAULT 0",
        "password_changed_at": "DATETIME NULL",
        "password_version": "INTEGER NOT NULL DEFAULT 0",
    }
    added_rotation_flag = "must_change_password" not in user_columns
    for name, definition in rotation_columns.items():
        if name not in user_columns:
            with bind.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE users ADD COLUMN {name} {definition}")
                )
    if added_rotation_flag and inspector.has_table("roles"):
        with bind.begin() as connection:
            connection.execute(text(
                "UPDATE users SET must_change_password=1 "
                "WHERE role_id IN (SELECT role_id FROM roles "
                "WHERE role_name IN ('SUPER_ADMIN','ADMIN'))"
            ))

def init_db():
    from app.models import all_models # noqa
    Base.metadata.create_all(bind=engine)
    migrate_admin_password_rotation(engine)
    inspector = inspect(engine)
    if inspector.has_table("cameras") and "camera_role" not in {column["name"] for column in inspector.get_columns("cameras")}:
        if engine.dialect.name not in {"mysql", "mariadb"}:
            raise RuntimeError("The camera-role migration requires MySQL or MariaDB.")
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE cameras ADD COLUMN camera_role "
                "ENUM('ENTRY','EXIT','PARKING_ZONE') NOT NULL DEFAULT 'PARKING_ZONE' AFTER location"
            ))

    if inspector.has_table("parking_records") and "active_vehicle_id" not in {
        column["name"] for column in inspector.get_columns("parking_records")
    }:
        if engine.dialect.name not in {"mysql", "mariadb"}:
            raise RuntimeError("The active-session migration requires MySQL or MariaDB.")
        with engine.connect() as connection:
            duplicates = connection.execute(text(
                "SELECT vehicle_id FROM parking_records WHERE status='PARKED' "
                "GROUP BY vehicle_id HAVING COUNT(*) > 1 LIMIT 1"
            )).first()
        if duplicates:
            raise RuntimeError(
                "Cannot enforce active-session uniqueness: duplicate active sessions exist. "
                "Resolve them manually before applying database/migrations/001_active_vehicle_unique_mysql.sql."
            )
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE parking_records ADD COLUMN active_vehicle_id INT "
                "GENERATED ALWAYS AS (CASE WHEN status='PARKED' THEN vehicle_id ELSE NULL END) STORED"
            ))
            connection.execute(text(
                "CREATE UNIQUE INDEX uq_parking_records_active_vehicle "
                "ON parking_records(active_vehicle_id)"
            ))

    from app.services.bootstrap import bootstrap
    with SessionLocal() as db:
        bootstrap(db)
