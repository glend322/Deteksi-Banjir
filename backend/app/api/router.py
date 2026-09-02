from fastapi import APIRouter
from app.api.endpoints import auth, users, flood, reports, routes, evacuation, weather, ai_bridge

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users & Profiles"])
api_router.include_router(flood.router, prefix="/flood", tags=["Flood Data & GIS"])
api_router.include_router(reports.router, prefix="/reports", tags=["Citizen Reports"])
api_router.include_router(routes.router, prefix="/routes", tags=["Safe Routing"])
api_router.include_router(evacuation.router, prefix="/evacuations", tags=["Evacuation Points"])
api_router.include_router(weather.router, prefix="/weather", tags=["Weather & Alerts"])
api_router.include_router(ai_bridge.router, prefix="/internal/ai", tags=["AI Integration Bridge"])
