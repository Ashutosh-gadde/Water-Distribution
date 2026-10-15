from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.permissions import Role


class LoginIn(BaseModel):
    employee_id: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotIn(BaseModel):
    employee_id: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    full_name: str
    email: str | None = None
    department: str | None = None
    designation: str | None = None
    role: str
    supervisor_id: int | None = None
    is_active: bool
    is_demo: bool
    last_login: datetime | None = None


class MeOut(UserOut):
    permissions: list[str]
    ward_ids: list[int]


class UserCreate(BaseModel):
    employee_id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    department: str | None = None
    designation: str | None = None
    role: Role
    password: str
    supervisor_id: int | None = None
    ward_ids: list[int] = []


class UserPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    department: str | None = None
    designation: str | None = None
    role: Role | None = None
    supervisor_id: int | None = None
    is_active: bool | None = None


class AssignIn(BaseModel):
    ward_id: int


class WardIn(BaseModel):
    code: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9._-]+$")
    name_en: str = Field(min_length=1, max_length=150)
    name_mr: str | None = None
    is_demo: bool = False
    notes: str | None = None


class WardOut(WardIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    verification_status: str
