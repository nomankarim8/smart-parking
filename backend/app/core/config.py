from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart AI-Based Vehicle Parking Management System" 
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "production"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "smart_parking_db"
    SECRET_KEY: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""
    PASSWORD_MIN_LENGTH: int = 12
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    OCR_ENABLED: bool = True
    PLATE_MODEL_PATH: str = "../ai-models/plate_yolo.pt"
    VEHICLE_MODEL_PATH: str = "../ai-models/vehicle_yolo.pt"
    ALPR_CONFIDENCE_THRESHOLD: float = 0.80
    AI_DEVICE: str = "cpu"
    ALPR_IMAGE_SIZE: int = 640
    PDF_FONT_PATH: str = ""
    BUSINESS_TIMEZONE: str = "Asia/Dhaka"
    MEDIA_ROOT: str = "uploads"
    DEMO_VIDEO_ROOT: str = "../demo-videos"
    CAMERA_ALLOWED_HOSTS: str = ""
    CAMERA_MAX_USB_INDEX: int = 8
    CAMERA_CREDENTIALS_KEY: str = ""
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    BENGALI_OCR_ENABLED: bool = True
    PAYMENT_MODE: str = "sandbox"
    BKASH_PERSONAL_NUMBER: str = ""
    NAGAD_PERSONAL_NUMBER: str = ""
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

    def validate_security_configuration(self) -> None:
        if self.APP_ENV not in {"development", "test", "production"}:
            raise RuntimeError("APP_ENV must be development, test, or production.")
        if self.APP_ENV != "development" and (
            len(self.SECRET_KEY) < 32
            or self.SECRET_KEY in {"change-me", "replace-with-a-long-random-secret"}
        ):
            raise RuntimeError(
                "SECRET_KEY must be a unique random value of at least 32 characters "
                "outside explicitly configured development mode."
            )
        if self.CAMERA_MAX_USB_INDEX < 0:
            raise RuntimeError("CAMERA_MAX_USB_INDEX must be zero or greater.")
        if self.PASSWORD_MIN_LENGTH < 12:
            raise RuntimeError("PASSWORD_MIN_LENGTH must be at least 12.")
        if not 0 < self.ALPR_CONFIDENCE_THRESHOLD <= 1:
            raise RuntimeError("ALPR_CONFIDENCE_THRESHOLD must be greater than zero and at most one.")
        if self.ALPR_IMAGE_SIZE < 160:
            raise RuntimeError("ALPR_IMAGE_SIZE must be at least 160 pixels.")

    @property
    def CAMERA_ALLOWED_HOST_SET(self) -> set[str]:
        return {
            host.strip().lower()
            for host in self.CAMERA_ALLOWED_HOSTS.split(",")
            if host.strip()
        }

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
