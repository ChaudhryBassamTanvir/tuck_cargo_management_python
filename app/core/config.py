from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "TruckCargoMS"
    DEBUG: bool = True
    SECRET_KEY: str
    DATABASE_URL: str
    SYNC_DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str
    DB_PASSWORD: str = "cargo_pass"

    class Config:
        env_file = ".env"

settings = Settings()