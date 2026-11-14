import os
from pydantic_settings import BaseSettings
from typing import Dict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Intelligent Omnichannel Ticket Routing & SLA Management"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./omnichannel.db")
    
    # Deterministic Seed
    DEFAULT_SEED: int = 20261022
    
    # Default Routing Scoring Weights
    WEIGHT_SKILL: float = 0.35
    WEIGHT_LANGUAGE: float = 0.25
    WEIGHT_CAPACITY: float = 0.25
    WEIGHT_EXPERIENCE: float = 0.15
    
    # SLA Response Targets in Minutes (P1, P2, P3, P4)
    SLA_FIRST_RESPONSE_MINUTES: Dict[str, int] = {
        "P1": 5,
        "P2": 15,
        "P3": 60,
        "P4": 240
    }
    
    # SLA Resolution Targets in Minutes
    SLA_RESOLUTION_MINUTES: Dict[str, int] = {
        "P1": 60,
        "P2": 240,
        "P3": 480,
        "P4": 1440
    }
    
    # Business Calendar
    BUSINESS_START_HOUR: int = 9
    BUSINESS_END_HOUR: int = 18
    BUSINESS_TIMEZONE: str = "Asia/Kolkata"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
