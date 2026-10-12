from typing import Optional, Literal
from sqlmodel import SQLModel, Field
from datetime import datetime

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int
    title: str
    due: Optional[datetime] = None
    status: str = "open"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Lead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    budget: Optional[float] = None
    stage: str = "new"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int
    to_name: str
    to_email: Optional[str] = None
    description: str
    amount: float
    status: str = "draft"
    stripe_checkout_url: Optional[str] = None
    stripe_checkout_id: Optional[str] = None
    stripe_checkout_status: Optional[str] = None
    stripe_payment_status: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserOrg(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    org_id: int
    role: Literal["owner","admin","member"] = "owner"

class OAuthAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    org_id: int
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None  # stores realmId for Intuit
    created_at: datetime = Field(default_factory=datetime.utcnow)

class APIKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int
    provider: str
    key: Optional[str] = None
    extra: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int
    name: str
    trigger_model: Literal["lead","task","invoice"]
    condition: str
    actions_json: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class JobLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int
    recipe_id: Optional[int] = None
    event: str
    status: str = "ok"
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
