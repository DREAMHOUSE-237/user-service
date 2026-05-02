"""
consume_identity_events
-----------------------
Listens to 'user_identified' queue published by the identity service.
The identity service sends only: email + status + requested_role.
We look up the user by email and upgrade their role accordingly.
"""
import json
import pika
import uuid
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from users.models import Utilisateur, ProcessedEvent

logger = logging.getLogger(__name__)
QUEUE_NAME = "user_identified"


class Command(BaseCommand):
    help = "Consume identity verification results from identity service"

    def handle(self, *args, **kwargs):
        params = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        self.stdout.write(self.style.SUCCESS(
            f"[*] Listening on '{QUEUE_NAME}' for identity results..."
        ))

        def callback(ch, method, properties, body):
            try:
                data     = json.loads(body)
                event_id = data.get("event_id", str(uuid.uuid4()))

                if ProcessedEvent.objects.filter(event_id=event_id).exists():
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                email            = data.get("email")
                status           = data.get("status")
                requested_role   = data.get("requested_role")
                rejection_reason = data.get("rejection_reason", "")

                with transaction.atomic():
                    try:
                        user = Utilisateur.objects.get(email=email)
                    except Utilisateur.DoesNotExist:
                        self.stdout.write(self.style.ERROR(
                            f"[!] No user found with email={email}"
                        ))
                        ProcessedEvent.objects.create(event_id=event_id)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    if status == "verified":
                        user.role          = requested_role   # e.g. "proprietaire"
                        user.is_identified = True
                        user.pending_role  = ""
                        user.save(update_fields=['role', 'is_identified', 'pending_role'])

                        self.stdout.write(self.style.SUCCESS(
                            f"[✓] {email} identified → role={requested_role}"
                        ))
                        self._send_approval_email(user, requested_role)

                    elif status == "rejected":
                        user.is_identified = False
                        user.save(update_fields=['is_identified'])

                        self.stdout.write(self.style.WARNING(
                            f"[✗] {email} identity rejected"
                        ))
                        self._send_rejection_email(user, rejection_reason)

                    ProcessedEvent.objects.create(event_id=event_id)

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as exc:
                logger.exception("Error processing identity event")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
        channel.start_consuming()

    def _send_approval_email(self, user, role):
        label = {'proprietaire': 'Propriétaire', 'agence': 'Agence Immobilière'}.get(role, role)
        try:
            send_mail(
                subject="DreamHouse237 — Identité vérifiée ✓",
                message=(
                    f"Bonjour,\n\n"
                    f"Votre identité a été vérifiée. "
                    f"Votre compte est maintenant actif en tant que {label}.\n\n"
                    f"L'équipe DreamHouse237"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning("Could not send approval email: %s", exc)

    def _send_rejection_email(self, user, reason):
        try:
            send_mail(
                subject="DreamHouse237 — Vérification d'identité refusée",
                message=(
                    f"Bonjour,\n\n"
                    f"Nous n'avons pas pu vérifier votre identité.\n"
                    f"Raison : {reason or 'Document non lisible ou invalide.'}\n\n"
                    f"Contactez le support pour resoumettre votre CNI.\n\n"
                    f"L'équipe DreamHouse237"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning("Could not send rejection email: %s", exc)
