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

        # 4. Vérifier si on est dans le master Gunicorn ou runserver
        is_gunicorn_master = str(os.getpid()) == os.environ.get("GUNICORN_MAIN_PID", "")
        is_runserver = os.environ.get("RUN_MAIN") == "true"

        if not is_gunicorn_master and not is_runserver:
            return

        # ── On est dans le processus principal ──
        start_rabbit = os.environ.get("START_RABBITMQ_CONSUMER", "false").lower() in ("1", "true", "yes", "on")

        if start_rabbit:
            self._start_thread(self._run_user_events_consumer, name="consumer-user-events")
            self._start_thread(self._run_identity_events_consumer, name="consumer-identity-events")

        self._start_thread(self._maybe_load_config, name="config-loader")
        self._start_thread(self._maybe_register_eureka, name="eureka-register")

    def _start_thread(self, target, name=None):
        t = threading.Thread(target=target, name=name or target.__name__, daemon=True)
        t.start()

    def _run_user_events_consumer(self):
        """Lance le consumer user_events directement sans call_command."""
        import json
        import pika
        import uuid
        from django.conf import settings

        # Attendre que Django soit complètement initialisé
        time.sleep(3)

        while True:
            try:
                from users.models import Utilisateur, ProcessedEvent
                from django.db import transaction

                rabbitmq_url = settings.RABBITMQ_URL
                params = pika.URLParameters(rabbitmq_url)
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.queue_declare(queue="user_auth_ack", durable=True)

                logger.info("[consumer] Waiting for auth ACK messages in 'user_auth_ack'...")

                def callback(ch, method, properties, body):
                    try:
                        data = json.loads(body)
                        event_id = data.get("event_id", str(uuid.uuid4()))

                        if ProcessedEvent.objects.filter(event_id=event_id).exists():
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            return

                        event_type = data.get("event", "")
                        with transaction.atomic():
                            if event_type == "user.auth_created":
                                user_service_id = data.get("user_service_id")
                                user_auth_id = data.get("user_auth_id")
                                if user_service_id and user_auth_id:
                                    Utilisateur.objects.filter(
                                        pk=user_service_id,
                                        user_auth_id__isnull=True,
                                    ).update(user_auth_id=str(user_auth_id))
                            ProcessedEvent.objects.create(event_id=event_id)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.error(f"Error in user_auth_ack callback: {e}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue="user_auth_ack", on_message_callback=callback)
                channel.start_consuming()

            except Exception as exc:
                logger.warning(f"[consumer-user-events] crashed: {exc} — retrying in 5s")
                time.sleep(5)

    def _run_identity_events_consumer(self):
        """Lance le consumer identity_events directement sans call_command."""
        import json
        import pika
        import uuid
        from django.conf import settings
        from django.core.mail import send_mail

        # Attendre que Django soit complètement initialisé
        time.sleep(3)

        while True:
            try:
                from users.models import Utilisateur, ProcessedEvent
                from django.db import transaction

                params = pika.URLParameters(settings.RABBITMQ_URL)
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.queue_declare(queue="user_identified", durable=True)

                logger.info("[consumer] Listening on 'user_identified' for identity results...")

                def callback(ch, method, properties, body):
                    try:
                        data = json.loads(body)
                        event_id = data.get("event_id", str(uuid.uuid4()))

                        if ProcessedEvent.objects.filter(event_id=event_id).exists():
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            return

                        email = data.get("email")
                        evt_status = data.get("status")
                        requested_role = data.get("requested_role")
                        rejection_reason = data.get("rejection_reason", "")
                        nom = data.get("nom", "")
                        prenom = data.get("prenom", "")
                        numero_cni = data.get("numero_cni", "")

                        with transaction.atomic():
                            try:
                                user = Utilisateur.objects.get(email=email)
                            except Utilisateur.DoesNotExist:
                                ProcessedEvent.objects.create(event_id=event_id)
                                ch.basic_ack(delivery_tag=method.delivery_tag)
                                return

                            if evt_status == "verified":
                                user.role = requested_role
                                user.is_identified = True
                                user.pending_role = ""
                                user.cni_nom = nom
                                user.cni_prenom = prenom
                                user.cni_numero = numero_cni
                                user.save(update_fields=[
                                    'role', 'is_identified', 'pending_role',
                                    'cni_nom', 'cni_prenom', 'cni_numero',
                                ])
                            elif evt_status == "rejected":
                                user.is_identified = False
                                user.save(update_fields=['is_identified'])

                            ProcessedEvent.objects.create(event_id=event_id)
                        ch.basic_ack(delivery_tag=method.delivery_tag)

                    except Exception as exc:
                        logger.exception(f"Error processing identity event: {exc}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue="user_identified", on_message_callback=callback)
                channel.start_consuming()

            except Exception as exc:
                logger.warning(f"[consumer-identity-events] crashed: {exc} — retrying in 5s")
                time.sleep(5)

    def _maybe_load_config(self):
        try:
            from .services import config_loader
            logger.info("Triggering config_loader.load_config()")
            config_loader.load_config()
        except Exception:
            logger.exception("Exception while calling config_loader.load_config()")

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