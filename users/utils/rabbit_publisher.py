# users/utils/rabbit_publisher.py
"""
CORRECTION : connexion RabbitMQ persistante.

Avant, chaque appel publish_message() ouvrait une nouvelle connexion TCP
et la refermait immédiatement. Appelé depuis le signal post_save(Profile),
cela créait des connexions en rafale sous charge → fuite mémoire + latence.

Maintenant : une seule connexion par processus, recréée automatiquement
si elle se ferme (timeout réseau, redémarrage RabbitMQ, etc.).
"""

import pika
import json
import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_connection = None
_channel    = None


def _get_channel():
    global _connection, _channel

    with _lock:
        if _connection is None or _connection.is_closed:
            logger.info("[RabbitMQ] Ouverture d'une nouvelle connexion...")
            _connection = pika.BlockingConnection(
                pika.URLParameters(settings.RABBITMQ_URL)
            )
            _channel = None

        if _channel is None or _channel.is_closed:
            _channel = _connection.channel()

        return _channel


# rabbit_publisher.py — remplacer publish_message() par

def publish_message(queue: str, message: dict) -> None:
    try:
        conn = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
        ch = conn.channel()
        ch.queue_declare(queue=queue, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        conn.close()
        logger.info("[RabbitMQ] Publié dans '%s' : %s", queue, message)
    except Exception as exc:
        logger.error("[RabbitMQ] Erreur publication : %s", exc)
        raise


# ── Helpers métier ─────────────────────────────────────────────────── #

def publish_to_auth_service(user, raw_password: str) -> None:
    message = {
        "event":           "user.register",
        "user_service_id": str(user.pk),   # ✅ CORRECTION : str() — cohérent avec CharField côté auth
        "email":           user.email,
        "password":        raw_password,
        "role":            user.role,
    }
    publish_message("user_created", message)
    logger.info("[→ auth] Registration event sent for %s", user.email)


def publish_user_to_publication(user, profile) -> None:
    # ✅ CORRECTION : ne pas publier si user_auth_id n'est pas encore connu.
    # Ce champ est renseigné de manière asynchrone par le consumer user_auth_ack
    # après que auth-service a créé son AuthUser. Publier avant expose un user_id
    # incohérent (str(pk) au lieu de l'UUID auth).
    if not user.user_auth_id:
        logger.warning(
            "[→ publication] Skipped: user_auth_id not yet set for %s — "
            "will be published once auth ACK is received.",
            user.email,
        )
        return

    try:
        region_display = dict(
            profile._meta.get_field("region").choices
        ).get(profile.region, profile.region)
    except Exception:
        region_display = profile.region

    message = {
        "user_id":              user.user_auth_id,   # UUID auth — identifiant global
        "email":                user.email,
        "role":                 user.role,
        "tel":                  user.tel,
        "nom":                  getattr(user, "nom", None),
        "prenom":               getattr(user, "prenom", None),
        "nomAgence":            getattr(user, "nomAgence", None),
        "nomPDG":               getattr(user, "nomPDG", None),
        "numeroIdentification": getattr(user, "numeroIdentification", None),
        "contactPrincipal":     getattr(user, "contactPrincipal", None),
        "region":               profile.region,
        "region_display":       region_display,
        "ville":                profile.ville,
        "quartier":             profile.quartier,
        "username":             profile.username,
        "is_verified":          user.is_verified,
    }
    publish_message("user-email-queue", message)
    logger.info("[→ publication] Profile sync sent for %s", user.email)