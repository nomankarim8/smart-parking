from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Numeric, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum

class RoleName(str,enum.Enum): SUPER_ADMIN="SUPER_ADMIN"; ADMIN="ADMIN"; OPERATOR="OPERATOR"; VIEWER="VIEWER"
class SlotStatus(str,enum.Enum): AVAILABLE="AVAILABLE"; OCCUPIED="OCCUPIED"; RESERVED="RESERVED"; MAINTENANCE="MAINTENANCE"
class ParkingStatus(str,enum.Enum): PARKED="PARKED"; COMPLETED="COMPLETED"; CANCELLED="CANCELLED"
class PaymentMethod(str,enum.Enum): CASH="CASH"; CARD="CARD"; MOBILE_BANKING="MOBILE_BANKING"; ONLINE="ONLINE"
class PaymentStatus(str,enum.Enum): PENDING="PENDING"; PAID="PAID"; FAILED="FAILED"; REFUNDED="REFUNDED"
class CameraType(str,enum.Enum): USB="USB"; IP="IP"; RTSP="RTSP"; UPLOAD="UPLOAD"; DEMO="DEMO"
class CameraStatus(str,enum.Enum): ONLINE="ONLINE"; OFFLINE="OFFLINE"; UNKNOWN="UNKNOWN"

class Role(Base):
    __tablename__="roles"
    role_id:Mapped[int]=mapped_column(primary_key=True); role_name:Mapped[str]=mapped_column(String(50),unique=True); description:Mapped[str|None]=mapped_column(String(255)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class User(Base):
    __tablename__="users"
    user_id:Mapped[int]=mapped_column(primary_key=True); username:Mapped[str]=mapped_column(String(50),unique=True,index=True); email:Mapped[str]=mapped_column(String(120),unique=True); password_hash:Mapped[str]=mapped_column(String(255)); full_name:Mapped[str]=mapped_column(String(120)); role_id:Mapped[int]=mapped_column(ForeignKey("roles.role_id")); is_active:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow); role=relationship("Role")
class VehicleCategory(Base):
    __tablename__="vehicle_categories"
    category_id:Mapped[int]=mapped_column(primary_key=True); category_name:Mapped[str]=mapped_column(String(50),unique=True); description:Mapped[str|None]=mapped_column(String(255)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Vehicle(Base):
    __tablename__="vehicles"
    vehicle_id:Mapped[int]=mapped_column(primary_key=True); plate_number:Mapped[str]=mapped_column(String(80)); normalized_plate:Mapped[str]=mapped_column(String(80),unique=True,index=True); category_id:Mapped[int]=mapped_column(ForeignKey("vehicle_categories.category_id")); owner_name:Mapped[str|None]=mapped_column(String(120)); owner_phone:Mapped[str|None]=mapped_column(String(30)); owner_email:Mapped[str|None]=mapped_column(String(120)); address:Mapped[str|None]=mapped_column(String(255)); vehicle_model:Mapped[str|None]=mapped_column(String(100)); vehicle_color:Mapped[str|None]=mapped_column(String(60)); registration_info:Mapped[str|None]=mapped_column(String(255)); notes:Mapped[str|None]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow); category=relationship("VehicleCategory")
class ParkingSlot(Base):
    __tablename__="parking_slots"
    slot_id:Mapped[int]=mapped_column(primary_key=True); slot_number:Mapped[str]=mapped_column(String(20),unique=True); category_id:Mapped[int]=mapped_column(ForeignKey("vehicle_categories.category_id")); status:Mapped[SlotStatus]=mapped_column(SAEnum(SlotStatus),default=SlotStatus.AVAILABLE); current_vehicle_id:Mapped[int|None]=mapped_column(ForeignKey("vehicles.vehicle_id",ondelete="SET NULL")); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow); category=relationship("VehicleCategory"); current_vehicle=relationship("Vehicle",foreign_keys=[current_vehicle_id])
class PricingRule(Base):
    __tablename__="pricing_rules"
    rule_id:Mapped[int]=mapped_column(primary_key=True); category_id:Mapped[int]=mapped_column(ForeignKey("vehicle_categories.category_id"),unique=True); hourly_rate:Mapped[float]=mapped_column(Numeric(10,2)); min_charge:Mapped[float]=mapped_column(Numeric(10,2),default=0); grace_period_minutes:Mapped[int]=mapped_column(Integer,default=15); daily_max_charge:Mapped[float|None]=mapped_column(Numeric(10,2)); overnight_charge:Mapped[float|None]=mapped_column(Numeric(10,2)); is_active:Mapped[bool]=mapped_column(Boolean,default=True)
class Camera(Base):
    __tablename__="cameras"
    camera_id:Mapped[int]=mapped_column(primary_key=True); camera_name:Mapped[str]=mapped_column(String(100),unique=True); location:Mapped[str]=mapped_column(String(160)); camera_type:Mapped[CameraType]=mapped_column(SAEnum(CameraType),default=CameraType.DEMO); stream_url:Mapped[str|None]=mapped_column(String(500)); status:Mapped[CameraStatus]=mapped_column(SAEnum(CameraStatus),default=CameraStatus.UNKNOWN); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class ParkingRecord(Base):
    __tablename__="parking_records"
    record_id:Mapped[int]=mapped_column(primary_key=True); vehicle_id:Mapped[int]=mapped_column(ForeignKey("vehicles.vehicle_id")); slot_id:Mapped[int]=mapped_column(ForeignKey("parking_slots.slot_id")); entry_time:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); exit_time:Mapped[datetime|None]=mapped_column(DateTime); entry_image_url:Mapped[str|None]=mapped_column(String(500)); exit_image_url:Mapped[str|None]=mapped_column(String(500)); plate_image_url:Mapped[str|None]=mapped_column(String(500)); raw_ocr_text:Mapped[str|None]=mapped_column(String(255)); ocr_confidence:Mapped[float|None]=mapped_column(Numeric(5,4)); status:Mapped[ParkingStatus]=mapped_column(SAEnum(ParkingStatus),default=ParkingStatus.PARKED); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow); vehicle=relationship("Vehicle"); slot=relationship("ParkingSlot")
class PlateDetection(Base):
    __tablename__="plate_detections"
    detection_id:Mapped[int]=mapped_column(primary_key=True); camera_id:Mapped[int|None]=mapped_column(ForeignKey("cameras.camera_id",ondelete="SET NULL")); parking_record_id:Mapped[int|None]=mapped_column(ForeignKey("parking_records.record_id",ondelete="SET NULL")); detected_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); raw_text:Mapped[str|None]=mapped_column(String(255)); normalized_plate:Mapped[str|None]=mapped_column(String(80),index=True); confidence:Mapped[float]=mapped_column(Numeric(5,4),default=0); image_url:Mapped[str|None]=mapped_column(String(500)); verification_status:Mapped[str]=mapped_column(String(30),default="MANUAL_REQUIRED")
class Payment(Base):
    __tablename__="payments"
    payment_id:Mapped[int]=mapped_column(primary_key=True); record_id:Mapped[int]=mapped_column(ForeignKey("parking_records.record_id"),unique=True); total_duration_minutes:Mapped[int]=mapped_column(Integer); gross_amount:Mapped[float]=mapped_column(Numeric(10,2)); discount_amount:Mapped[float]=mapped_column(Numeric(10,2),default=0); net_amount:Mapped[float]=mapped_column(Numeric(10,2)); payment_method:Mapped[PaymentMethod]=mapped_column(SAEnum(PaymentMethod)); payment_status:Mapped[PaymentStatus]=mapped_column(SAEnum(PaymentStatus),default=PaymentStatus.PENDING); transaction_reference:Mapped[str|None]=mapped_column(String(120)); payment_time:Mapped[datetime|None]=mapped_column(DateTime); created_by:Mapped[int|None]=mapped_column(ForeignKey("users.user_id",ondelete="SET NULL")); record=relationship("ParkingRecord")
class Blacklist(Base):
    __tablename__="blacklist"
    blacklist_id:Mapped[int]=mapped_column(primary_key=True); plate_number:Mapped[str]=mapped_column(String(80),unique=True,index=True); reason:Mapped[str]=mapped_column(String(255)); is_active:Mapped[bool]=mapped_column(Boolean,default=True); added_by:Mapped[int]=mapped_column(ForeignKey("users.user_id")); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); notes:Mapped[str|None]=mapped_column(Text)
class Notification(Base):
    __tablename__="notifications"
    notification_id:Mapped[int]=mapped_column(primary_key=True); title:Mapped[str]=mapped_column(String(150)); message:Mapped[str]=mapped_column(String(500)); severity:Mapped[str]=mapped_column(String(20),default="INFO"); is_read:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); created_by:Mapped[int|None]=mapped_column(ForeignKey("users.user_id",ondelete="SET NULL"))
class ActivityLog(Base):
    __tablename__="activity_logs"
    log_id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int|None]=mapped_column(ForeignKey("users.user_id",ondelete="SET NULL")); action:Mapped[str]=mapped_column(String(120)); entity_type:Mapped[str|None]=mapped_column(String(80)); entity_id:Mapped[int|None]=mapped_column(Integer); details:Mapped[dict|None]=mapped_column(JSON); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
