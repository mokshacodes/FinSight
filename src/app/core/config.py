from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./database.db"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()