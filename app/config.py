import os
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
class Settings(BaseModel):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "keyops_session")
    DB_PATH: str = os.getenv("DB_PATH", "keyops_plus.db")
    OAUTH_REDIRECT_BASE: str = os.getenv("OAUTH_REDIRECT_BASE", "http://127.0.0.1:8009")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    XAI_API_KEY: str | None = os.getenv("XAI_API_KEY")
    OLLAMA_BASE_URL: str | None = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    STRIPE_CLIENT_ID: str | None = os.getenv("STRIPE_CLIENT_ID")
    STRIPE_CLIENT_SECRET: str | None = os.getenv("STRIPE_CLIENT_SECRET")
    INTUIT_CLIENT_ID: str | None = os.getenv("INTUIT_CLIENT_ID")
    INTUIT_CLIENT_SECRET: str | None = os.getenv("INTUIT_CLIENT_SECRET")
settings = Settings()
