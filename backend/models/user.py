"""
models/user.py — Pydantic models for user registration, authentication, and profiles.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ─── Enums ────────────────────────────────────────────────────────────


class UserRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    ADMIN = "admin"
    SENIOR_ENGINEER = "senior_engineer"


class UserTier(str, Enum):
    FREE = "Free"
    STANDARD = "Standard"
    PREMIUM = "Premium"
    ENTERPRISE = "Enterprise"


# ─── Request schemas ──────────────────────────────────────────────────


class UserRegister(BaseModel):
    """Body for POST /api/auth/register."""

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    role: UserRole = UserRole.USER
    tier: UserTier = UserTier.STANDARD  # for regular users
    # Agent-specific: list of domains they can handle
    skills: Optional[List[str]] = []

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Basic password strength check."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if v.isdigit():
            raise ValueError("Password cannot be all digits — add a letter")
        if v.isalpha():
            raise ValueError("Password must contain at least one number")
        return v


class UserLogin(BaseModel):
    """Body for POST /api/auth/login."""

    email: EmailStr
    password: str


class UserPasswordChange(BaseModel):
    """Body for PATCH /api/users/me/password."""

    current_password: str
    new_password: str = Field(min_length=8)


# ─── Database document ────────────────────────────────────────────────


class UserDocument(BaseModel):
    """
    Full user document stored in MongoDB users collection.
    password_hash is NEVER returned in API responses.
    """

    user_id: str  # UUID
    name: str
    email: str
    password_hash: str  # bcrypt hash — never expose in API
    role: UserRole = UserRole.USER
    tier: UserTier = UserTier.STANDARD  # for ticket SLA + priority logic

    # Agent performance stats (null for regular users)
    skills: List[str] = []  # domain names agent can handle
    current_load: int = 0  # active tickets assigned
    max_load: int = 10  # configurable limit
    avg_resolution_time: Optional[float] = None  # hours
    tickets_resolved_total: int = 0
    approval_rate: Optional[float] = None  # % of AI suggestions approved

    # HITL Enhancement: department & expertise
    department: List[str] = []  # departments agent belongs to
    expertise_tags: List[str] = []  # fine-grained expertise tags
    availability_status: str = "ONLINE"  # ONLINE / BUSY / OFFLINE

    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True

    class Config:
        use_enum_values = True


# ─── Response schemas ─────────────────────────────────────────────────


class UserProfile(BaseModel):
    """Public profile returned by GET /api/auth/me. No password_hash."""

    user_id: str
    name: str
    email: str
    role: str
    tier: str
    skills: List[str] = []
    current_load: int = 0
    max_load: int = 10
    avg_resolution_time: Optional[float] = None
    tickets_resolved_total: int = 0
    approval_rate: Optional[float] = None
    department: List[str] = []
    expertise_tags: List[str] = []
    availability_status: str = "ONLINE"
    created_at: datetime
    is_active: bool


class AgentSummary(BaseModel):
    """Condensed agent info for admin dashboard."""

    user_id: str
    name: str
    email: str
    skills: List[str]
    current_load: int
    max_load: int
    avg_resolution_time: Optional[float]
    tickets_resolved_total: int
    approval_rate: Optional[float]
    department: List[str] = []
    expertise_tags: List[str] = []
    availability_status: str = "ONLINE"
    is_active: bool


class UserUpdate(BaseModel):
    """Body for PATCH /api/admin/agents/{id} — updatable fields only."""

    name: Optional[str] = None
    skills: Optional[List[str]] = None
    max_load: Optional[int] = Field(default=None, ge=1, le=100)
    is_active: Optional[bool] = None
    tier: Optional[UserTier] = None
    department: Optional[List[str]] = None
    expertise_tags: Optional[List[str]] = None
    availability_status: Optional[str] = None  # ONLINE / BUSY / OFFLINE
