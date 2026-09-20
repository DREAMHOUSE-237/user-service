import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")
django.setup()

from users.utils.rabbit_publisher import publish_message

message = {
    "event_id": "test123",
    "user_id": "abc123",
    "email": "test@example.com",
    "role": "proprietaire",
    "tel": "123456789",
    "nom": "John",
    "prenom": "Doe",
    "localisation": "Yaounde",
    "numeroIdentification": "ID987654",
    "nomPDG": "",
    "contactPrincipal": "",
    "nomAgence": "",
    "nomUtilisateur": "johndoe",
}

publish_message("user_created", message)
print("Test message sent.")
