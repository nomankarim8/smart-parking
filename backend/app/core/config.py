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
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    BENGALI_OCR_ENABLED: bool = True
    PAYMENT_MODE: str = "sandbox"
    PAYMENT_CALLBACK_BASE_URL: str = ""
    PAYMENT_RETURN_URL: str = "http://localhost:5173/payment-result"
    PAYMENT_DEMO_ENABLED: bool = False
    BKASH_BASE_URL: str = "https://tokenized.sandbox.bka.sh/v2/tokenized-checkout"
    BKASH_USERNAME: str = ""
    BKASH_PASSWORD: str = ""
    BKASH_APP_KEY: str = ""
    BKASH_APP_SECRET: str = ""
    NAGAD_BASE_URL: str = "http://sandbox.mynagad.com:10080/remote-payment-gateway-1.0/api/dfs"
    NAGAD_MERCHANT_ID: str = ""
    NAGAD_MERCHANT_NUMBER: str = ""
    NAGAD_HOST_IP: str = ""
    NAGAD_PUBLIC_KEY: str = ""
    NAGAD_PRIVATE_KEY: str = ""
    TWILIO_SMS_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
