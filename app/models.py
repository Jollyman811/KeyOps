from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    due: Optional[datetime] = None
    status: str = "open"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Lead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
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
    to_name: str
    description: str
    amount: float
    status: str = "draft"   # draft, sent, paid
    created_at: datetime = Field(default_factory=datetime.utcnow)
