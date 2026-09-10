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

def init_db():
    from app.models import all_models # noqa
    Base.metadata.create_all(bind=engine)
    # Backward-compatible migration for databases created before camera roles existed.
    try:
        inspector = inspect(engine)
        if inspector.has_table("cameras") and "camera_role" not in {c["name"] for c in inspector.get_columns("cameras")}:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE cameras ADD COLUMN camera_role ENUM('ENTRY','EXIT','PARKING_ZONE') NOT NULL DEFAULT 'PARKING_ZONE' AFTER location"))
    except Exception:
        # Keep startup resilient; the explicit SQL migration remains available.
        pass
    from app.services.bootstrap import bootstrap
    with SessionLocal() as db:
        bootstrap(db)
