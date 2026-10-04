from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/daycompass"
    jwt_secret: str = "REPLACE_WITH_A_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"

settings = Settings()
