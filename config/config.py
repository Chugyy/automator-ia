# app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = Field(env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")
    host: str = Field(env="HOST")
    port: int = Field(8000, env="PORT")
    database_url: str = Field(env="DATABASE_URL")
    class Config:
        env_file = "config/.env"
        env_file_encoding = "utf-8"

settings = Settings()