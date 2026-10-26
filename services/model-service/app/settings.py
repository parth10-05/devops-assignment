from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    local_artifacts_dir: str = "/app/artifacts"
    log_level: str = "INFO"
