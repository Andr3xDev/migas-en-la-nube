from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_ENVIRONMENT = "local"
LOCAL_IMAGES_CONTAINER_URL = "https://images.local/images"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDC_")

    version: str = "0.1.0"
    environment: str = LOCAL_ENVIRONMENT
    cosmos_connection_string: str = ""
    jwt_key: str = ""
    storage_connection_string: str = ""
    images_container_url: str = LOCAL_IMAGES_CONTAINER_URL
    login_failure_delay_seconds: float = 0.5


@cache
def get_settings() -> Settings:
    return Settings()
