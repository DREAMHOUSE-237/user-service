import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Utilisateur, Profile, Proprietaire, AgenceImmobiliere, Client

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Profile auto-creation
# ─────────────────────────────────────────────────────────────────

def build_profile(instance):
    data = {
        'utilisateur': instance,
        'email':    instance.email,
        'contact':  instance.tel,
        'username': instance.email.split("@")[0],
    }

    if isinstance(instance, Proprietaire):
        data['username'] = f"{instance.nom} {instance.prenom}"
        data['ville']    = instance.ville
        data['quartier'] = instance.quartier
        data['region']   = instance.region

    elif isinstance(instance, AgenceImmobiliere):
        data['username']             = instance.nomAgence
        data['ville']                = instance.ville
        data['quartier']             = instance.quartier
        data['region']               = instance.region
        data['numeroIdentification'] = instance.numeroIdentification
        data['nomPDG']               = instance.nomPDG

    elif isinstance(instance, Client):
        data['username'] = f"{instance.nom} {instance.prenom}"
        data['ville']    = instance.ville
        data['quartier'] = instance.quartier
        data['region']   = instance.region

    return data


@receiver(post_save, sender=Utilisateur)
@receiver(post_save, sender=Proprietaire)
@receiver(post_save, sender=AgenceImmobiliere)
@receiver(post_save, sender=Client)
def create_profile(sender, instance, created, **kwargs):
    """Automatically create a Profile after any user is created."""
    if not created or hasattr(instance, 'profile'):
        return
    Profile.objects.create(**build_profile(instance))


@receiver(post_delete, sender=Utilisateur)
def delete_profile_with_user(sender, instance, **kwargs):
    try:
        instance.profile.delete()
    except Profile.DoesNotExist:
        pass


# ─────────────────────────────────────────────────────────────────
# Publish to publication service after profile save
# ─────────────────────────────────────────────────────────────────

@receiver(post_save, sender=Profile)
def publish_profile_to_publication_service(sender, instance, **kwargs):
    """
    Every time a Profile is saved (created or updated), push the combined
    payload to the publication service via RabbitMQ.

    ✅ CORRECTION : publish_user_to_publication gère elle-même la garde
    sur user_auth_id. Si l'ACK auth n'est pas encore arrivé, le publish
    est ignoré (avec log WARNING). Il sera déclenché à nouveau par
    re_publish_after_auth_link ci-dessous dès réception de l'ACK.
    """
    try:
        from .utils.rabbit_publisher import publish_user_to_publication
        publish_user_to_publication(instance.utilisateur, instance)
    except Exception as exc:
        logger.warning("Could not publish profile to publication service: %s", exc)


# ─────────────────────────────────────────────────────────────────
# ✅ CORRECTION : re-publish vers publication service dès que
# user_auth_id est renseigné (après réception ACK de auth-service).
# ─────────────────────────────────────────────────────────────────

@receiver(post_save, sender=Utilisateur)
@receiver(post_save, sender=Proprietaire)
@receiver(post_save, sender=AgenceImmobiliere)
@receiver(post_save, sender=Client)
def re_publish_after_auth_link(sender, instance, created, update_fields, **kwargs):
    """
    Déclenché quand user_auth_id vient d'être écrit par le consumer user_auth_ack.
    À ce moment, user_auth_id est disponible → on peut publier vers publication service.
    """
    if created:
        return  # création initiale : user_auth_id pas encore connu, pas de publish

    # On ne réagit que si c'est bien user_auth_id qui vient d'être mis à jour
    if update_fields is None or "user_auth_id" not in update_fields:
        return

    try:
        profile = instance.profile
    except Profile.DoesNotExist:
        logger.warning("[signal] re_publish_after_auth_link: no profile for %s", instance.email)
        return

    try:
        from .utils.rabbit_publisher import publish_user_to_publication
        publish_user_to_publication(instance, profile)
        logger.info(
            "[signal] re_publish_after_auth_link: profile sync sent for %s (user_auth_id=%s)",
            instance.email, instance.user_auth_id,
        )
    except Exception as exc:
        logger.warning("Could not re-publish profile after auth link for %s: %s", instance.email, exc)