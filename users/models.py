import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password as django_check_password


# ------------------------------------------------------------------
# Regions of Cameroon — used as a fixed choice list across all models
# ------------------------------------------------------------------
REGIONS_CAMEROUN = [
    ('adamaoua',     'Adamaoua'),
    ('centre',       'Centre'),
    ('est',          'Est'),
    ('extreme_nord', 'Extrême-Nord'),
    ('littoral',     'Littoral'),
    ('nord',         'Nord'),
    ('nord_ouest',   'Nord-Ouest'),
    ('ouest',        'Ouest'),
    ('sud',          'Sud'),
    ('sud_ouest',    'Sud-Ouest'),
]

ROLE_CHOICES = [
    ('admin',                'Admin'),
    ('proprietaire',         'Propriétaire'),
    ('agence',               'Agence Immobilière'),
    ('client',               'Client'),
    ('pending_proprietaire', 'Pending Propriétaire'),
    ('pending_agence',       'Pending Agence'),
]


class Utilisateur(models.Model):
    user_auth_id = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        help_text="UUID assigned by the authentication service"
    )
    email         = models.EmailField(unique=True)
    mot_de_passe  = models.CharField(max_length=255)   # stored hashed
    tel           = models.CharField(max_length=20, null=True, blank=True)
    role          = models.CharField(max_length=50)
    is_active     = models.BooleanField(default=True)

    # ── Email verification ──────────────────────────────────────────
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="One-time token sent by email for account verification"
    )

    # ── Identity verification (CNI scan by identity service) ────────
    is_identified = models.BooleanField(
        default=False,
        help_text="True once the identity service has verified the CNI"
    )
    pending_role = models.CharField(
        max_length=50, blank=True, default='',
        help_text="Desired role awaiting identity confirmation"
    )

    # ── CNI data stored from identity service ───────────────────────
    cni_nom      = models.CharField(max_length=150, blank=True, default='')
    cni_prenom   = models.CharField(max_length=150, blank=True, default='')
    cni_numero   = models.CharField(max_length=100, blank=True, default='')

    date_creation = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        """Hash the password before storing."""
        self.mot_de_passe = make_password(raw_password)

    def check_password(self, raw_password):
        return django_check_password(raw_password, self.mot_de_passe)

    def __str__(self):
        return f"{self.email} ({self.role})"


class Proprietaire(Utilisateur):
    nom      = models.CharField(max_length=100)
    prenom   = models.CharField(max_length=100)
    ville    = models.CharField(max_length=150, null=True, blank=True)
    quartier = models.CharField(max_length=150, null=True, blank=True)
    region   = models.CharField(
        max_length=50, choices=REGIONS_CAMEROUN, null=True, blank=True,
    )


class AgenceImmobiliere(Utilisateur):
    nomAgence            = models.CharField(max_length=100)
    ville                = models.CharField(max_length=150, null=True, blank=True)
    quartier             = models.CharField(max_length=150, null=True, blank=True)
    region               = models.CharField(
        max_length=50, choices=REGIONS_CAMEROUN, null=True, blank=True,
    )
    numeroIdentification = models.CharField(max_length=50)
    nomPDG               = models.CharField(max_length=100)
    contactPrincipal     = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Agence Immobilière"
        verbose_name_plural = "Agences Immobilières"


class Client(Utilisateur):
    nom      = models.CharField(max_length=100)
    prenom   = models.CharField(max_length=100)
    ville    = models.CharField(max_length=150, null=True, blank=True)
    quartier = models.CharField(max_length=150, null=True, blank=True)
    region   = models.CharField(
        max_length=50, choices=REGIONS_CAMEROUN, null=True, blank=True,
    )

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"


class Admin(Utilisateur):
    """
    Admin user — can manage all users and manually validate pending CNI identities.
    """
    nom    = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Admin"
        verbose_name_plural = "Admins"


class Profile(models.Model):
    utilisateur = models.OneToOneField(
        'Utilisateur', on_delete=models.CASCADE, related_name='profile'
    )
    username = models.CharField(max_length=150)
    photo    = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    contact  = models.CharField(max_length=50, null=True, blank=True)
    email    = models.EmailField(null=True, blank=True)

    # Location — shared by all roles
    ville    = models.CharField(max_length=150, null=True, blank=True)
    quartier = models.CharField(max_length=150, null=True, blank=True)
    region   = models.CharField(
        max_length=50, choices=REGIONS_CAMEROUN, null=True, blank=True,
    )

    # Agency-specific
    numeroIdentification = models.CharField(max_length=50, null=True, blank=True)
    nomPDG               = models.CharField(max_length=100, null=True, blank=True)

    @property
    def user_auth_id(self):
        return self.utilisateur.user_auth_id

    def __str__(self):
        return self.username


class ProcessedEvent(models.Model):
    event_id     = models.CharField(max_length=128, unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id
