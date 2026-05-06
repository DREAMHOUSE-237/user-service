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
            # IMPORTANT : les consumers eux-mêmes ne doivent pas se relancer
            "consume_user_events", "consume_identity_events",
        }
        if any(cmd in sys.argv for cmd in mgmt_commands_to_skip):
            return

        # ──────────────────────────────────────────────────────────────────
        # CORRECTION PRINCIPALE
        #
        # AVANT (problème) :
        #   Le guard "RUN_MAIN=true" était censé protéger contre les doubles
        #   lancements, mais dans Docker avec Gunicorn, RUN_MAIN=true est une
        #   variable d'ENVIRONNEMENT du conteneur (définie dans docker-compose).
        #   → Elle est visible par TOUS les workers Gunicorn.
        #   → Chaque worker appelait ready() et lançait 2 subprocesses Django
        #     (consume_user_events + consume_identity_events) = ~150 MB chacun.
        #   → Avec --workers 2 : 4 subprocesses = ~600 MB rien que pour les consumers.
        #
        # APRÈS (correction) :
        #   On utilise os.getpid() == os.getppid()-based detection via
        #   la variable GUNICORN_WORKER_PID. Gunicorn expose _worker_id sur
        #   l'objet arbiter. La méthode la plus fiable est d'utiliser un
        #   fichier lock ou de détecter le master via PPID.
        #
        #   Solution simple et robuste : on injecte GUNICORN_MAIN_PID dans
        #   le Dockerfile CMD, et on compare avec os.getpid().
        #   Si PIDs correspondent → on est dans le master → on lance les threads.
        #   Si PIDs diffèrent → on est dans un worker forké → on skip.
        #
        #   Pour le dev server Django (runserver), RUN_MAIN=true est injecté
        #   uniquement par le processus enfant de reloader → OK.
        # ──────────────────────────────────────────────────────────────────

        is_gunicorn_master = str(os.getpid()) == os.environ.get("GUNICORN_MAIN_PID", "")
        is_runserver       = os.environ.get("RUN_MAIN") == "true"

        # En dehors de runserver et gunicorn master → on est dans un worker, on skip
        if not is_gunicorn_master and not is_runserver:
            return

        # ── Désormais on est CERTAIN d'être dans le processus principal ──

        start_rabbit = os.environ.get("START_RABBITMQ_CONSUMER", "false").lower() in ("1", "true", "yes", "on")

        if start_rabbit:
            # CORRECTION : threads au lieu de subprocesses
            # subprocess.Popen([sys.executable, "manage.py", "consume_..."]) créait
            # une instance Django complète (~150 MB) par consumer, par worker.
            # Les threads partagent la mémoire du processus principal → ~5 MB chacun.
            self._start_thread(self._run_user_events_consumer,    name="consumer-user-events")
            self._start_thread(self._run_identity_events_consumer, name="consumer-identity-events")

        self._start_thread(self._maybe_load_config,    name="config-loader")
        self._start_thread(self._maybe_register_eureka, name="eureka-register")

    # ------------------------------------------------------------------ #
    def _start_thread(self, target, name=None):
        t = threading.Thread(target=target, name=name or target.__name__, daemon=True)
        t.start()

    # ──────────────────────────────────────────────────────────────────
    # Consumers RabbitMQ — maintenant des THREADS, plus des subprocesses
    # ──────────────────────────────────────────────────────────────────

    def _run_user_events_consumer(self):
        """Lance consume_user_events directement en thread (sans subprocess)."""
        import django
        from django.core.management import call_command
        try:
            logger.info("[consumer] Starting consume_user_events thread...")
            call_command("consume_user_events")
        except Exception as exc:
            logger.exception("consume_user_events thread crashed: %s", exc)

    def _run_identity_events_consumer(self):
        """Lance consume_identity_events directement en thread (sans subprocess)."""
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