# users/apps.py
import os
import sys
import threading
import subprocess
import logging
import time
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)

class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception:
            logger.exception("Failed to import signals")

        if getattr(settings, "TESTING", False):
            return

        if os.environ.get("RUN_MAIN") != "true":
            return

        mgmt_commands_to_skip = {"makemigrations", "migrate", "collectstatic", "test", "shell"}
        if any(cmd in sys.argv for cmd in mgmt_commands_to_skip):
            return

        # ---------- DEV SETTINGS ----------
        start_rabbit = os.environ.get("START_RABBITMQ_CONSUMER", "false").lower() in ("1", "true", "yes", "on")
        start_config = True
        start_eureka = True

        if start_rabbit:
            self._start_thread(self._maybe_start_rabbitmq_consumer, name="start-rmq-consumer")
            self._start_thread(self._maybe_start_identity_consumer, name="start-identity-consumer")
        if start_config:
            self._start_thread(self._maybe_load_config, name="config-loader")
        if start_eureka:
            self._start_thread(self._maybe_register_eureka, name="eureka-register")

    def _start_thread(self, target, name=None):
        t = threading.Thread(target=target, name=name or target.__name__, daemon=True)
        t.start()

    # ---------- RabbitMQ consumer ----------
    def _maybe_start_rabbitmq_consumer(self):
        try:
            logger.info("Starting RabbitMQ consumer subprocess...")
            subprocess.Popen(
                [sys.executable, "manage.py", "consume_user_events"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as exc:
            logger.exception("Failed to start RabbitMQ consumer subprocess: %s", exc)

    # ---------- Identity events consumer ----------
    def _maybe_start_identity_consumer(self):
        try:
            logger.info("Starting identity events consumer subprocess...")
            subprocess.Popen(
                [sys.executable, "manage.py", "consume_identity_events"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as exc:
            logger.exception("Failed to start identity consumer subprocess: %s", exc)

    # ---------- Config loader ----------
    def _maybe_load_config(self):
        try:
            from .services import config_loader
            logger.info("Triggering config_loader.load_config()")
            config_loader.load_config()
        except Exception:
            logger.exception("Exception while calling config_loader.load_config()")

    # ---------- Eureka registration ----------
    def _maybe_register_eureka(self):
        try:
            from .services import eureka
        except Exception:
            logger.exception("Could not import eureka service; skipping registration.")
            return

        max_attempts = int(os.environ.get("EUREKA_REG_MAX_ATTEMPTS", "6"))
        base_wait = float(os.environ.get("EUREKA_REG_BASE_WAIT", "2.0"))

        for attempt in range(1, max_attempts + 1):
            try:
                eureka.register()
                logger.info("Eureka registration successful.")

                # ----------------------------------------------
                # NEW: Start heartbeat loop after registration
                # ----------------------------------------------
                self._start_thread(eureka.start_heartbeat_loop, name="eureka-heartbeat")

                return
            except Exception as exc:
                wait = base_wait * (2 ** (attempt - 1))
                logger.warning(
                    "Eureka registration attempt %d failed: %s — retrying in %.1f seconds",
                    attempt,
                    exc,
                    wait,
                )
                time.sleep(wait)

        logger.error("Eureka registration failed after %d attempts.", max_attempts)
