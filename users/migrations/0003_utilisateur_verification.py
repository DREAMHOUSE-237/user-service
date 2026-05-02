"""
Migration 0003
--------------
- user_auth_id becomes nullable (filled later by auth ACK)
- Add is_verified (default False)
- Add verification_token (UUID, unique, auto-generated)
"""
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_location_fields_and_client'),
    ]

    operations = [
        # user_auth_id: allow null so records exist before auth echoes back
        migrations.AlterField(
            model_name='utilisateur',
            name='user_auth_id',
            field=models.CharField(
                blank=True,
                help_text='UUID assigned by the authentication service',
                max_length=128,
                null=True,
                unique=True,
            ),
        ),

        # Email verification flag
        migrations.AddField(
            model_name='utilisateur',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),

        # One-time verification token
        migrations.AddField(
            model_name='utilisateur',
            name='verification_token',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                help_text='One-time token sent by email for account verification',
                unique=True,
            ),
        ),
    ]
