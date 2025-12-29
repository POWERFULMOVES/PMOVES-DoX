from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    model_name: str = os.getenv("MODEL_NAME", "mock")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")

settings = Settings()
