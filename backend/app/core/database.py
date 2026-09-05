from sqlalchemy import create_engine
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
    from app.services.bootstrap import bootstrap
    with SessionLocal() as db:
        bootstrap(db)
