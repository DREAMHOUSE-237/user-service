import pika
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def publish_message(queue, message):
    """Low-level: publish any JSON message to a named queue."""
    params = pika.URLParameters(settings.RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),  # persistent
    )
    connection.close()
    logger.info("Published to queue '%s': %s", queue, message)


def publish_to_auth_service(user, raw_password):
    """
    Tell the auth service to create its AuthUser record.
    Queue: user_created
    """
    message = {
        "event":          "user.register",
        "user_service_id": user.pk,
        "email":           user.email,
        "password":        raw_password,
        "role":            user.role,
    }
    publish_message("user_created", message)
    logger.info("[→ auth] Registration event sent for %s", user.email)


def publish_user_to_publication(user, profile):
    """
    Publish user data to the publication service.
    Combines what auth service used to send + email/region we were already sending.
    Queue: user_profile_sync
    """
    region_display = dict(
        profile._meta.get_field('region').choices
    ).get(profile.region, profile.region)

    message = {
        # ── what auth service was sending ──────────────────────────
        "user_id": user.user_auth_id or str(user.pk),
        "email": user.email,
        "role": user.role,
        "tel": user.tel,

        # ── role-specific fields ───────────────────────────────────
        "nom": getattr(user, 'nom', None),
        "prenom": getattr(user, 'prenom', None),
        "nomAgence": getattr(user, 'nomAgence', None),
        "nomPDG": getattr(user, 'nomPDG', None),
        "numeroIdentification": getattr(user, 'numeroIdentification', None),
        "contactPrincipal": getattr(user, 'contactPrincipal', None),

        # ── what we were already sending ──────────────────────────
        "region": profile.region,
        "region_display": region_display,

        # ── extra profile fields ───────────────────────────────────
        "ville": profile.ville,
        "quartier": profile.quartier,
        "username": profile.username,
        "is_verified": user.is_verified,
    }
    publish_message("user_profile_sync", message)
    logger.info("[→ publication] Profile sync sent for %s", user.email)
