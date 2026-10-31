import os
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Solar Installation Management System (SunPower ERP)"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/solar_erp")
    MEDIA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "media"
    
    # Configurable default warranty durations (in months)
    WARRANTY_DURATION_MONTHS: dict = {
        "Inverter": 24,           # 2 years
        "Battery": 24,            # 2 years
        "Charge Controller": 24,  # 2 years
        "Solar Panels": 240,      # 20 years (bulk warranty per order)
    }

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
