from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

CameraRole = Literal["ENTRY", "EXIT", "PARKING_ZONE"]
CameraType = Literal["USB", "IP", "RTSP", "UPLOAD", "DEMO"]
CameraStatus = Literal["ONLINE", "OFFLINE", "UNKNOWN"]


class CameraCreate(BaseModel):
    camera_name: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=160)
    camera_role: CameraRole = "PARKING_ZONE"
    camera_type: CameraType = "DEMO"
    stream_url: Optional[str] = None


class CameraUpdate(BaseModel):
    camera_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    location: Optional[str] = Field(default=None, min_length=2, max_length=160)
    camera_role: Optional[CameraRole] = None
    camera_type: Optional[CameraType] = None
    stream_url: Optional[str] = None


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    camera_id: int
    camera_name: str
    location: str
    camera_role: str
    camera_type: str
    stream_configured: bool
    status: str
    created_at: datetime
    updated_at: datetime
