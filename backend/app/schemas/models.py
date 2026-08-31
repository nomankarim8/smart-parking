from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class VehicleIn(BaseModel):
    plate_number: str = Field(min_length=3,max_length=80)
    category_id: int
    owner_name: str|None = None
    owner_phone: str|None = None
    owner_email: EmailStr|None = None
    address: str|None = None
    vehicle_model: str|None = None
    vehicle_color: str|None = None
    registration_info: str|None = None
    notes: str|None = None

class VehicleOut(VehicleIn):
    model_config = ConfigDict(from_attributes=True)
    vehicle_id: int
    normalized_plate: str
    created_at: datetime

class EntryIn(BaseModel):
    license_plate: str = Field(min_length=3,max_length=80)
    category_id: int
    ocr_confidence: float|None = Field(default=None,ge=0,le=1)
    raw_ocr_text: str|None = None
    entry_image_url: str|None = None
    plate_image_url: str|None = None

class EntryOut(BaseModel):
    record_id: int
    license_plate: str
    slot: str
    entry_time: datetime
    status: str
    blacklist_alert: bool = False

class ExitIn(BaseModel):
    license_plate: str = Field(min_length=3,max_length=80)
    payment_method: str = "CASH"
    discount: float = Field(default=0,ge=0)
    exit_image_url: str|None = None
    transaction_reference: str|None = None

class ExitOut(BaseModel):
    record_id: int
    license_plate: str
    slot: str
    entry_time: datetime
    exit_time: datetime
    duration_minutes: int
    gross_amount: float
    discount_amount: float
    net_amount: float
    payment_status: str
    payment_method: str

class ALPRResponse(BaseModel):
    license_plate: str
    normalized_plate: str
    raw_text: str
    confidence: float
    status: str
    verification_required: bool
    detector: str
