"""
RegistrationService
-------------------
1. Validates email uniqueness
2. Creates the typed user with hashed password
   - proprietaire/agence: role stored as 'pending_proprietaire'/'pending_agence'
     until the identity service confirms via RabbitMQ
   - client: role set immediately, no identity check needed
3. Publishes credentials to auth service via RabbitMQ
4. Sends verification email to the user
"""
import logging
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail

from ..models import Utilisateur, Proprietaire, AgenceImmobiliere, Client

logger = logging.getLogger(__name__)

ROLES_REQUIRING_IDENTITY = {'proprietaire', 'agence'}


class RegistrationService:

    @transaction.atomic
    def register(self, role, raw_password, **fields):
        email = fields.get('email')
        if not email:
            raise ValueError("email is required.")

        if Utilisateur.objects.filter(email=email).exists():
            raise ValueError(f"Un utilisateur avec l'email '{email}' existe déjà.")

        role = role.lower()

        # ── 1. Create user ────────────────────────────────────────────
        user = self._create_user(role, raw_password, fields)

        # ── 2. Notify auth service ─────────────────────────────────────
        try:
            from ..utils.rabbit_publisher import publish_to_auth_service
            publish_to_auth_service(user, raw_password)
        except Exception as exc:
            logger.warning("[registration] Could not notify auth service: %s", exc)

        # ── 3. Send email verification ─────────────────────────────────
        try:
            self._send_verification_email(user)
        except Exception as exc:
            logger.warning("[registration] Could not send verification email: %s", exc)

        return user

    def _create_user(self, role, raw_password, fields):
        needs_identity = role in ROLES_REQUIRING_IDENTITY
        actual_role    = f"pending_{role}" if needs_identity else role
        pending_role   = role if needs_identity else ""

        common = {
            'email':        fields['email'],
            'tel':          fields.get('tel'),
            'role':         actual_role,
            'pending_role': pending_role,
            'ville':        fields.get('ville'),
            'quartier':     fields.get('quartier'),
            'region':       fields.get('region'),
        }

        if role == 'proprietaire':
            user = Proprietaire(nom=fields['nom'], prenom=fields['prenom'], **common)
        elif role == 'agence':
            user = AgenceImmobiliere(
                nomAgence=fields['nomAgence'],
                numeroIdentification=fields['numeroIdentification'],
                nomPDG=fields['nomPDG'],
                contactPrincipal=fields['contactPrincipal'],
                **common,
            )
        elif role == 'client':
            user = Client(nom=fields['nom'], prenom=fields['prenom'], **common)
        else:
            raise ValueError(f"Rôle inconnu: '{role}'. Choisir parmi: proprietaire, agence, client.")

        user.set_password(raw_password)
        user.save()
        logger.info("[registration] Created user %s (role=%s)", user.email, user.role)
        return user

    def _send_verification_email(self, user):
        base_url   = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:8000')
        verify_url = f"{base_url}/users/verify-email/{user.verification_token}/"

        extra = ""
        if user.role.startswith("pending_"):
            extra = (
                "\n\nNote: votre rôle sera activé après vérification de votre CNI. "
                "Soumettez vos documents sur la page de vérification d'identité."
            )

        send_mail(
            subject="DreamHouse237 — Vérifiez votre adresse email",
            message=(
                f"Bonjour,\n\n"
                f"Cliquez sur ce lien pour activer votre compte :\n{verify_url}"
                f"{extra}\n\n"
                f"L'équipe DreamHouse237"
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=False,
        )
