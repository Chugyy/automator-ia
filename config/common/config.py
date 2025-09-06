# app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = Field("MonSuperAPI", env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")
    host: str = Field("127.0.0.1", env="HOST")
    port: int = Field(8000, env="PORT")
    version: str = Field("dev", env="VERSION")
    database_url: str = Field("sqlite:///./database.db", env="DATABASE_URL")
    secret_key: str = Field("dev-secret-key-change-in-prod", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    class Config:
        env_file = "config/common/.env"
        env_file_encoding = "utf-8"

settings = Settings()