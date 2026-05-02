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
    """
    try:
        from .utils.rabbit_publisher import publish_user_to_publication
        publish_user_to_publication(instance.utilisateur, instance)
    except Exception as exc:
        logger.warning("Could not publish profile to publication service: %s", exc)
