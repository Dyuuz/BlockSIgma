import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra    = "ignore",    # ← this lets you have other keys in .env
    )

settings = Settings()

import redis
from urllib.parse import urlparse


# Parse the REDIS_URL
redis_url = os.getenv('REDIS_URL')
parsed_url = urlparse(redis_url)

print(redis_url)
REDIS_HOST = parsed_url.hostname
REDIS_PORT = parsed_url.port
REDIS_PASSWORD = parsed_url.password
REDIS_DB = 0  # Default DB unless you need a specific one

try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    
    # Test the connection
    # redis_client.ping()
    print("✅ Successfully connected to Redis!")
except redis.exceptions.ConnectionError as e:
    print(f"❌ Could not connect to Redis: {e}. Signals will not be persisted.")
    redis_client = None
except Exception as e:
    print(f"❌ Unexpected error connecting to Redis: {e}")
    redis_client = None

