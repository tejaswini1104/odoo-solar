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

    # Advance required before installation, as a percentage of the quotation total including GST
    ADVANCE_PERCENT: float = 30.0

    # The company's own clock. Timestamps are stored in UTC, but "today", "this week" and date ranges mean a day
    # in India, which is 5 hours 30 minutes ahead of UTC and has no daylight saving.
    BUSINESS_UTC_OFFSET_MINUTES: int = 330

    # Out-of-warranty repairs: the visit and labour charge added to the price of the faulty part, before GST
    SERVICE_LABOUR_CHARGE: float = 1500.0
    GST_PERCENT: float = 18.0

    # Proof of a finished installation
    MIN_INSTALLATION_PHOTOS: int = 1
    MAX_PHOTO_BYTES: int = 8 * 1024 * 1024
    MAX_SIGNATURE_BYTES: int = 300 * 1024

    # Shown to customers for bank transfers. Replace these placeholders with the company's real bank details.
    BANK_DETAILS: dict = {
        "account_name": "SunPower Solutions",
        "bank_name": "TO BE CONFIGURED",
        "account_number": "TO BE CONFIGURED",
        "ifsc": "TO BE CONFIGURED",
        "upi_id": "TO BE CONFIGURED",
    }

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
