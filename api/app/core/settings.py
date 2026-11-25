from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDC_")

    version: str = "0.1.0"
    environment: str = "local"
    cosmos_connection_string: str = ""
    jwt_key: str = ""
    storage_connection_string: str = ""
    images_container_url: str = ""
    login_failure_delay_seconds: float = 0.5
