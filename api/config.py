from pathlib import Path

from pydantic_settings import BaseSettings

WORKSHOP_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{WORKSHOP_DIR / 'data' / 'workshop.db'}"
    schematics_root: str = str(WORKSHOP_DIR.parent)
    mouser_api_key: str = ""
    digikey_client_id: str = ""
    digikey_client_secret: str = ""
    poll_interval: int = 21600
    design_files_dir: str = str(WORKSHOP_DIR / "data" / "design_files")

    model_config = {"env_file": str(WORKSHOP_DIR / ".env"), "extra": "ignore"}


settings = Settings()
