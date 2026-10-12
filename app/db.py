from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "keyops.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

def init_db():
    from . import models  # ensure models are imported
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
