"""
consume_user_events
-------------------
Listens to events coming FROM the auth service.

Auth service publishes two event types:
  1. "user.auth_created"  — auth has successfully created its AuthUser record;
                            it echoes back the user_service_id + the new UUID
                            so we can store user_auth_id on our Utilisateur.
  2. (future) any other auth-side events

NOTE: The user service no longer creates users by consuming a queue.
      User creation now happens through POST /users/register/ directly.
      This consumer only handles auth-service callbacks.
"""
import json
import pika
import uuid
from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import Utilisateur, ProcessedEvent
from django.db import transaction

QUEUE_NAME = "user_auth_ack"   # auth service publishes here after creating AuthUser


class Command(BaseCommand):
    help = "Consume auth-service acknowledgement events"

    def handle(self, *args, **kwargs):
        rabbitmq_url = settings.RABBITMQ_URL
        params = pika.URLParameters(rabbitmq_url)

        self.stdout.write(self.style.SUCCESS(
            f"Connecting to RabbitMQ at {rabbitmq_url}"
        ))

        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        self.stdout.write(self.style.SUCCESS(
            f"[*] Waiting for auth ACK messages in '{QUEUE_NAME}'..."
        ))

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
                        # Auth service has created its AuthUser and sends back:
                        #   user_service_id  → our local PK
                        #   user_auth_id     → the UUID from auth service
                        user_service_id = data.get("user_service_id")
                        user_auth_id    = data.get("user_auth_id")

                        if user_service_id and user_auth_id:
                            updated = Utilisateur.objects.filter(
                                pk=user_service_id,
                                user_auth_id__isnull=True,
                            ).update(user_auth_id=str(user_auth_id))

                            if updated:
                                self.stdout.write(self.style.SUCCESS(
                                    f"[✓] Linked user PK={user_service_id} "
                                    f"→ user_auth_id={user_auth_id}"
                                ))
                            else:
                                self.stdout.write(self.style.WARNING(
                                    f"[!] No unlinked user found for PK={user_service_id}"
                                ))

                    else:
                        self.stdout.write(f"[?] Unknown event type: {event_type} — skipped")

                    ProcessedEvent.objects.create(event_id=event_id)

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
        channel.start_consuming()
