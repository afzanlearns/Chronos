import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    CHRONOS_ENV: str = os.getenv("CHRONOS_ENV", "development")
    DB_PATH: str = os.getenv("CHRONOS_DB_PATH", str(Path.home() / ".chronos" / "chronos.db"))
    CONFIG_PATH: str = os.getenv("CHRONOS_CONFIG_PATH", str(Path.home() / ".chronos" / "config.yml"))
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "true").lower() == "true"


settings = Settings()
