from fastapi import APIRouter
from app.api.v1.endpoints import auth,vehicles,slots,parking,alpr,dashboard,blacklist,cameras,reports,settings,reservations,notifications,payments,sensors,audit
api_router=APIRouter()
api_router.include_router(auth.router,prefix="/auth",tags=["Authentication"]); api_router.include_router(vehicles.router,prefix="/vehicles",tags=["Vehicles"]); api_router.include_router(slots.router,prefix="/slots",tags=["Parking Slots"]); api_router.include_router(parking.router,prefix="/parking",tags=["Parking"]); api_router.include_router(alpr.router,prefix="/alpr",tags=["ALPR"]); api_router.include_router(dashboard.router,prefix="/dashboard",tags=["Dashboard"]); api_router.include_router(blacklist.router,prefix="/blacklist",tags=["Blacklist"]); api_router.include_router(cameras.router,prefix="/cameras",tags=["Cameras"]); api_router.include_router(reports.router,prefix="/reports",tags=["Reports"]); api_router.include_router(settings.router,prefix="/settings",tags=["Settings"])
api_router.include_router(reservations.router,prefix="/reservations",tags=["Reservations"])
api_router.include_router(notifications.router,prefix="/notifications",tags=["Notifications"])
api_router.include_router(payments.router,prefix="/payments",tags=["Payments"])
api_router.include_router(sensors.router,prefix="/sensors",tags=["Sensors"])
api_router.include_router(audit.router,prefix="/audit",tags=["Admin Audit"])
