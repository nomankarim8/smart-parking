from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart AI-Based Vehicle Parking Management System"
    API_V1_STR: str = "/api/v1"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "smart_parking_db"
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    OCR_ENABLED: bool = True
    PLATE_MODEL_PATH: str = "../ai-models/plate_yolo.pt"
    VEHICLE_MODEL_PATH: str = "../ai-models/vehicle_yolo.pt"
    ALPR_CONFIDENCE_THRESHOLD: float = 0.80
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
