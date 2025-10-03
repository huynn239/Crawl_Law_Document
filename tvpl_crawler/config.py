from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    base_url: str = os.getenv("BASE_URL", "https://thuvienphapluat.vn")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "20"))
    rate_limit_per_sec: float = float(os.getenv("RATE_LIMIT_PER_SEC", "1.0"))

settings = Settings()
