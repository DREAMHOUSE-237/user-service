# users/apps.py
import os
import sys
import threading
import logging
import time
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        # 1. Toujours importer les signals
        try:
            from . import signals  # noqa: F401
        except Exception:
            logger.exception("Failed to import signals")

        # 2. Jamais pendant les tests
        if getattr(settings, "TESTING", False):
            return

        # 3. Jamais pendant les commandes de gestion
        mgmt_commands_to_skip = {
            "makemigrations", "migrate", "collectstatic", "test", "shell",
            "consume_user_events", "consume_identity_events",
        }
        if any(cmd in sys.argv for cmd in mgmt_commands_to_skip):
            return

        is_gunicorn_master = str(os.getpid()) == os.environ.get("GUNICORN_MAIN_PID", "")
        is_runserver       = os.environ.get("RUN_MAIN") == "true"

        if not is_gunicorn_master and not is_runserver:
            return

        start_rabbit = os.environ.get("START_RABBITMQ_CONSUMER", "false").lower() in ("1", "true", "yes", "on")

        if start_rabbit:
            self._start_thread(self._run_user_events_consumer,     name="consumer-user-events")
            self._start_thread(self._run_identity_events_consumer,  name="consumer-identity-events")

        self._start_thread(self._maybe_load_config,     name="config-loader")
        self._start_thread(self._maybe_register_eureka, name="eureka-register")

    # ------------------------------------------------------------------ #
    def _start_thread(self, target, name=None):
        t = threading.Thread(target=target, name=name or target.__name__, daemon=True)
        t.start()

    # ------------------------------------------------------------------ #
    # Consumers RabbitMQ
    # ------------------------------------------------------------------ #

    def _run_user_events_consumer(self):
        """Lance consume_user_events en thread. Le sleep initial laisse Django
        terminer le chargement de tous ses modules avant tout import concurrent,
        ce qui évite le _DeadlockError sur user_service.urls."""
        time.sleep(3)  # ← CORRECTION : garde anti-deadlock
        from django.core.management import call_command
        try:
            logger.info("[consumer] Starting consume_user_events thread...")
            call_command("consume_user_events")
        except Exception as exc:
            logger.exception("consume_user_events thread crashed: %s", exc)

    def _run_identity_events_consumer(self):
        """Lance consume_identity_events en thread."""
        time.sleep(3)  # ← CORRECTION : garde anti-deadlock
        from django.core.management import call_command
        try:
            logger.info("[consumer] Starting consume_identity_events thread...")
            call_command("consume_identity_events")
        except Exception as exc:
            logger.exception("consume_identity_events thread crashed: %s", exc)

    # ------------------------------------------------------------------ #
    # Config loader
    # ------------------------------------------------------------------ #

    def _maybe_load_config(self):
        time.sleep(1)  # ← CORRECTION : garde anti-deadlock
        try:
            from .services import config_loader
            logger.info("Triggering config_loader.load_config()")
            config_loader.load_config()
        except Exception:
            logger.exception("Exception while calling config_loader.load_config()")

    # ------------------------------------------------------------------ #
    # Eureka registration + heartbeat
    # ------------------------------------------------------------------ #

    def _maybe_register_eureka(self):
        time.sleep(2)  # ← CORRECTION : garde anti-deadlock (critique)
        try:
            from .services import eureka
        except Exception:
            logger.exception("Could not import eureka service; skipping registration.")
            return

        max_attempts = int(os.environ.get("EUREKA_REG_MAX_ATTEMPTS", "6"))
        base_wait    = float(os.environ.get("EUREKA_REG_BASE_WAIT", "2.0"))

        for attempt in range(1, max_attempts + 1):
            try:
                eureka.register()
                logger.info("Eureka registration successful.")
                self._start_thread(eureka.start_heartbeat_loop, name="eureka-heartbeat")
                return
            except Exception as exc:
                wait = base_wait * (2 ** (attempt - 1))
                logger.warning(
                    "Eureka registration attempt %d failed: %s — retrying in %.1f seconds",
                    attempt, exc, wait,
                )
                time.sleep(wait)

        logger.error("Eureka registration failed after %d attempts.", max_attempts)