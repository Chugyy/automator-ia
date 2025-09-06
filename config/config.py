# app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = Field("AutomatorIA", env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(10000, env="PORT")
    version: str = Field("dev", env="VERSION")
    database_url: str = Field("sqlite:///./database.db", env="DATABASE_URL")
    class Config:
        env_file = "config/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore les variables d'environnement non déclarées

settings = Settings()