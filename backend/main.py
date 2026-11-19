from fastapi import FastAPI
from datetime import datetime, timezone
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def startup():
    settings.validate_security_configuration()
    init_db()
  
@app.get("/")
def root():
    return {"system": settings.PROJECT_NAME, "status": "online", "docs": "/docs", "version": "1.0.0"}

@app.get("/health")
def health():
    try:
        from app.core.database import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        database_status = "connected"
        status = "online"
    except Exception:
        database_status = "unavailable"
        status = "degraded"
    return {
        "status": status,
        "database": database_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
