from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDC_")

    version: str = "0.1.0"
    environment: str = "local"
