"""
RabbitMQ Publisher avec connexion persistante par process.

- 1 connexion par worker Django
- reconnexion automatique si crash
- retry sur publish
- thread-safe
"""

import json
import logging
import threading
import time

import pika
from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_connection = None
_channel = None


# ────────────────────────────────────────────────
# CONNECTION MANAGER
# ────────────────────────────────────────────────

def _connect():
    global _connection, _channel

    logger.info("[RabbitMQ] Ouverture connexion...")

    _connection = pika.BlockingConnection(
        pika.URLParameters(settings.RABBITMQ_URL)
    )
    _channel = _connection.channel()


def _get_channel():
    global _connection, _channel

    with _lock:
        try:
            if _connection is None or _connection.is_closed:
                _connect()

            if _channel is None or _channel.is_closed:
                _channel = _connection.channel()

        except Exception as exc:
            logger.warning("[RabbitMQ] Connexion cassée → reset: %s", exc)
            _connection = None
            _channel = None
            _connect()

        return _channel


# ────────────────────────────────────────────────
# PUBLISH CORE (RETRY SAFE)
# ────────────────────────────────────────────────

def publish_message(queue: str, message: dict, retries: int = 3) -> None:
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            ch = _get_channel()

            ch.queue_declare(queue=queue, durable=True)

            ch.basic_publish(
                exchange="",
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2
                ),
            )

            logger.info("[RabbitMQ] Publié dans '%s'", queue)
            return

        except Exception as exc:
            last_error = exc

            logger.error(
                "[RabbitMQ] Tentative %s/%s échouée: %s",
                attempt,
                retries,
                exc
            )

            with _lock:
                global _connection, _channel
                try:
                    if _connection:
                        _connection.close()
                except Exception:
                    pass

                _connection = None
                _channel = None

            time.sleep(1 * attempt)

    raise RuntimeError(
        f"[RabbitMQ] Échec après {retries} tentatives: {last_error}"
    )


# ────────────────────────────────────────────────
# BUSINESS HELPER
# ────────────────────────────────────────────────

def publish_to_auth_service(user, raw_password: str) -> None:
    """
    Publie event user.register vers auth-service.
    """

    # SAFE region_display (aucune dépendance à choices)
    region_display = getattr(user, "region_display", None) or user.region

    message = {
        "event": "user.register",
        "user_service_id": str(user.pk),
        "email": user.email,
        "password": raw_password,
        "role": user.role,
        "region": user.region,
        "region_display": region_display,
    }

    publish_message("user_created", message)

    logger.info("[→ auth] Registration event sent for %s", user.email)