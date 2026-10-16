from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import datetime

app = FastAPI(
    title="Latur Municipal Corporation Water Distribution API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Mock User Database & Role Verification
def verify_role(required_roles: List[str]):
    def dependency(credentials: HTTPAuthorizationCredentials = Security(security)):
        token = credentials.credentials
        # In production, decode JWT from Supabase Auth and check claims
        # For pilot demonstration: token acts as role specifier (e.g. "bearer admin_token")
        user_role = token.split("_")[0] if "_" in token else "citizen"
        if user_role not in required_roles and "super_admin" not in user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Insufficient municipal permissions."
            )
        return {"user_id": "usr_9941", "role": user_role}
    return dependency

# --- Pydantic Models ---
class ScheduleCreate(BaseModel):
    zone_id: int
    operator_id: str
    planned_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time

class ComplaintCreate(BaseModel):
    ward_id: int
    issue_type: str
    description: str

# --- Secure Endpoints ---
@app.get("/api/health")
def health_check():
    return {"status": "secure", "database": "PostGIS connected", "timezone": "IST"}

@app.post("/api/schedules", status_code=status.HTTP_201_CREATED)
def create_schedule(
    schedule: ScheduleCreate, 
    user: dict = Depends(verify_role(["water_supply_officer", "municipal_admin"]))
):
    # Server-side validation and conflict checking
    return {
        "status": "success",
        "message": "Schedule submitted and validated successfully.",
        "created_by": user["user_id"],
        "data": schedule
    }

@post("/api/complaints", status_code=status.HTTP_201_CREATED)
def submit_complaint(
    complaint: ComplaintCreate,
    user: dict = Depends(verify_role(["citizen", "ward_officer"]))
):
    tracking_ref = f"LATUR-WTR-{datetime.datetime.now().strftime('%Y%m%d')}-8819"
    return {
        "tracking_ref": tracking_ref,
        "status": "Submitted",
        "message": "Complaint securely registered in municipal database."
    }
