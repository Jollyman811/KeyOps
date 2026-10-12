from sqlmodel import SQLModel, create_engine, Session
from .config import settings
engine = create_engine(f"sqlite:///{settings.DB_PATH}", echo=False, connect_args={"check_same_thread": False})
def init_db():
    from . import models
    SQLModel.metadata.create_all(engine)
def get_session():
    return Session(engine)
