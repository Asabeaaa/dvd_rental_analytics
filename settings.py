from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    This class uses pydantic's BaseSettings to load environment variables or default values
    for application configuration.
    """
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_NAME: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def load_settings():
    return Settings()


settings = load_settings()
