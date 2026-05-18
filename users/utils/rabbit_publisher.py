"""
Connexion RabbitMQ persistante par processus.

Une seule connexion TCP est maintenue et partagée entre tous les appels.
Elle est recréée automatiquement si elle se ferme (timeout réseau,
redémarrage RabbitMQ, etc.).

Helpers métier disponibles :
  - publish_to_auth_service(user, profile, raw_password)
      → publie l'événement "user.register" vers l'auth service
        avec les données d'inscription complètes (email, password,
        role, région, user_service_id).
"""

import json
import logging
import threading

import pika
from django.conf import settings

logger = logging.getLogger(__name__)

_lock       = threading.Lock()
_connection = None
_channel    = None


# ── Connexion persistante ───────────────────────────────────────────── #

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


# ── Publication bas niveau ──────────────────────────────────────────── #

def publish_message(queue: str, message: dict) -> None:
    """
    Publie un message JSON dans la queue RabbitMQ indiquée.
    La queue est déclarée durable si elle n'existe pas encore.
    En cas d'erreur, la connexion est réinitialisée pour le prochain appel.
    """
    try:
        ch = _get_channel()
        ch.queue_declare(queue=queue, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),  # message persistant
        )
        logger.info("[RabbitMQ] Publié dans '%s' : %s", queue, message)

    except Exception as exc:
        # Réinitialiser la connexion pour que le prochain appel recrée proprement
        global _connection, _channel
        with _lock:
            _connection = None
            _channel    = None
        logger.error("[RabbitMQ] Erreur — connexion réinitialisée : %s", exc)
        raise


# ── Helper métier ───────────────────────────────────────────────────── #

def publish_to_auth_service(user, raw_password: str) -> None:
    """
    Publie l'événement d'inscription vers l'auth service (queue "user_created").

    Champs envoyés :
        event            — identifiant de l'événement
        user_service_id  — PK Django (str) de l'utilisateur dans ce service
        email            — adresse email
        password         — mot de passe en clair (hashé côté auth service)
        role             — rôle de l'utilisateur
        region           — code région (ex: "CE", "LT", ...)
        region_display   — libellé complet de la région
    """
    try:
        region_display = dict(
            user._meta.get_field("region").choices
        ).get(user.region, user.region)
    except Exception:
        region_display = user.region

    message = {
        "event":            "user.register",
        "user_service_id":  str(user.pk),   # str() — cohérent avec CharField côté auth
        "email":            user.email,
        "password":         raw_password,
        "role":             user.role,
        "region":           user.region,
        "region_display":   region_display,
    }
    publish_message("user_created", message)
    logger.info("[→ auth] Registration event envoyé pour %s", user.email)