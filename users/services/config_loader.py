import requests
import os
import logging
import threading

logger = logging.getLogger(__name__)

CONFIG_SERVER_URL = os.environ.get("CONFIG_SERVER_URL", "http://192.168.172.22:8080")
APP_NAME = os.environ.get("APP_NAME", "USER-SERVICE")
PROFILE = os.environ.get("PROFILE", "dev")

cached_config = {}
_lock = threading.Lock()

def load_config():
    """Fetch external config from Spring Cloud Config Server."""
    def _fetch():
        global cached_config
        url = f"{CONFIG_SERVER_URL}/{APP_NAME}/{PROFILE}"
        logger.info(f"Fetching config from: {url}")

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            merged = {}
            for src in data.get("propertySources", []):
                merged.update(src.get("source", {}))

            with _lock:
                cached_config = merged
            logger.info("Config fetched successfully.")

        except Exception as e:
            logger.error(f"Failed to fetch config: {e}")

    # Run in background thread so Django doesn't block
    threading.Thread(target=_fetch, daemon=True).start()

def get_config(key, default=None):
    """Retrieve a config value safely from cached_config."""
    with _lock:
        return cached_config.get(key, default)
