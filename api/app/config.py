import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    title: str = os.getenv("API_TITLE", "Cakra Aksara API")
    description: str = os.getenv(
        "API_DESCRIPTION",
        "Universal AI Intelligence Layer",
    )
    version: str = os.getenv("API_VERSION", "0.1.0")
    environment: str = os.getenv("API_ENV", "development")


settings = Settings()
