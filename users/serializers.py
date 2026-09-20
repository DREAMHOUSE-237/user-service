from rest_framework import serializers
from .models import Utilisateur, Proprietaire, AgenceImmobiliere, Client, Admin, Profile, REGIONS_CAMEROUN

USER_ACTIONS = ["user.created", "user.updated", "user.deleted", "user.read"]
REGIONS_DICT = {key: label for key, label in REGIONS_CAMEROUN}


class RegisterProprietaireSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    tel      = serializers.CharField(required=False, allow_blank=True)
    nom      = serializers.CharField()
    prenom   = serializers.CharField()
    ville    = serializers.CharField(required=False, allow_blank=True)
    quartier = serializers.CharField(required=False, allow_blank=True)
    region   = serializers.ChoiceField(choices=REGIONS_CAMEROUN, required=False, allow_null=True)


class RegisterAgenceSerializer(serializers.Serializer):
    email                = serializers.EmailField()
    password             = serializers.CharField(write_only=True, min_length=6)
    tel                  = serializers.CharField(required=False, allow_blank=True)
    nomAgence            = serializers.CharField()
    ville                = serializers.CharField(required=False, allow_blank=True)
    quartier             = serializers.CharField(required=False, allow_blank=True)
    region               = serializers.ChoiceField(choices=REGIONS_CAMEROUN, required=False, allow_null=True)
    numeroIdentification = serializers.CharField()
    nomPDG               = serializers.CharField()
    contactPrincipal     = serializers.CharField()


class RegisterClientSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    tel      = serializers.CharField(required=False, allow_blank=True)
    nom      = serializers.CharField()
    prenom   = serializers.CharField()
    ville    = serializers.CharField(required=False, allow_blank=True)
    quartier = serializers.CharField(required=False, allow_blank=True)
    region   = serializers.ChoiceField(choices=REGIONS_CAMEROUN, required=False, allow_null=True)


class RegisterAdminSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    tel      = serializers.CharField(required=False, allow_blank=True)
    nom      = serializers.CharField()
    prenom   = serializers.CharField()


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Utilisateur
        fields = '__all__'
        extra_kwargs = {
            'mot_de_passe':       {'write_only': True},
            'tel':                {'required': False, 'allow_null': True},
            'verification_token': {'read_only': True},
        }


class ProprietaireSerializer(serializers.ModelSerializer):
    region_display = serializers.CharField(source='get_region_display', read_only=True)

    class Meta:
        model  = Proprietaire
        fields = '__all__'
        extra_kwargs = {
            'mot_de_passe':       {'write_only': True},
            'verification_token': {'read_only': True},
        }


class AgenceImmobiliereSerializer(serializers.ModelSerializer):
    region_display = serializers.CharField(source='get_region_display', read_only=True)

    class Meta:
        model  = AgenceImmobiliere
        fields = '__all__'
        extra_kwargs = {
            'mot_de_passe':       {'write_only': True},
            'verification_token': {'read_only': True},
        }


class ClientSerializer(serializers.ModelSerializer):
    region_display = serializers.CharField(source='get_region_display', read_only=True)

    class Meta:
        model  = Client
        fields = '__all__'
        extra_kwargs = {
            'mot_de_passe':       {'write_only': True},
            'verification_token': {'read_only': True},
        }


class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Admin
        fields = '__all__'
        extra_kwargs = {
            'mot_de_passe':       {'write_only': True},
            'verification_token': {'read_only': True},
        }


class ProfileSerializer(serializers.ModelSerializer):
    region_display = serializers.CharField(source='get_region_display', read_only=True)

    class Meta:
        model  = Profile
        fields = '__all__'
        read_only_fields = ['utilisateur', 'username', 'email']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        role = getattr(instance.utilisateur, 'role', '').lower()
        base = ['id', 'utilisateur', 'username', 'email', 'contact',
                'photo', 'region', 'region_display', 'ville', 'quartier']
        if role in ['agence', 'agenceimmobiliere', 'agence immobilière']:
            allowed = base + ['numeroIdentification', 'nomPDG']
        else:
            allowed = base
        return {k: v for k, v in data.items() if k in allowed}

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


# ── Admin manual CNI validation serializer ──────────────────────── #

class AdminValidateCNISerializer(serializers.Serializer):
    """
    Used by admin to manually validate a user's identity.
    The admin must enter the 3 CNI fields for the unidentified user.
    """
    user_id    = serializers.IntegerField(help_text="ID of the Utilisateur to validate")
    nom        = serializers.CharField(help_text="Nom (surname) from CNI")
    prenom     = serializers.CharField(help_text="Prénom (given name) from CNI")
    numero_cni = serializers.CharField(help_text="CNI number")
    action     = serializers.ChoiceField(
        choices=['approve', 'reject'],
        help_text="'approve' to validate, 'reject' to refuse"
    )
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get('action') == 'approve':
            missing = [f for f in ['nom', 'prenom', 'numero_cni'] if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError(
                    {f: "Ce champ est requis pour l'approbation." for f in missing}
                )
        return attrs


class UpdateUserSerializer(serializers.Serializer):
    """
    Serializer pour la modification des informations personnelles d'un utilisateur.
    Tous les champs sont optionnels sauf l'email et seuls les champs fournis seront mis à jour.
    Le mot de passe nécessite la confirmation de l'ancien mot de passe.
    """
    # Champs communs à tous les rôles
    tel      = serializers.CharField(required=False, allow_blank=True)

    # Changement de mot de passe
    ancien_mot_de_passe  = serializers.CharField(required=False, write_only=True)
    nouveau_mot_de_passe = serializers.CharField(required=False, write_only=True, min_length=6)

    # Champs pour Proprietaire / Client / Admin
    nom      = serializers.CharField(required=False, allow_blank=True)
    prenom   = serializers.CharField(required=False, allow_blank=True)

    # Champs pour Proprietaire / Client / AgenceImmobiliere
    ville    = serializers.CharField(required=False, allow_blank=True)
    quartier = serializers.CharField(required=False, allow_blank=True)
    region   = serializers.ChoiceField(choices=REGIONS_CAMEROUN, required=False, allow_null=True)

    # Champs spécifiques à AgenceImmobiliere
    nomAgence        = serializers.CharField(required=False, allow_blank=True)
    nomPDG           = serializers.CharField(required=False, allow_blank=True)
    contactPrincipal = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Si l'un des champs mot de passe est fourni, les deux sont obligatoires
        ancien  = attrs.get('ancien_mot_de_passe')
        nouveau = attrs.get('nouveau_mot_de_passe')
        if ancien and not nouveau:
            raise serializers.ValidationError(
                {"nouveau_mot_de_passe": "Ce champ est requis pour changer le mot de passe."}
            )
        if nouveau and not ancien:
            raise serializers.ValidationError(
                {"ancien_mot_de_passe": "L'ancien mot de passe est requis pour en définir un nouveau."}
            )
        return attrs


class UserEventSerializer(serializers.Serializer):
    event_id    = serializers.CharField(max_length=128)
    source      = serializers.CharField()
    action      = serializers.ChoiceField(choices=USER_ACTIONS)
    occurred_at = serializers.DateTimeField()
    data        = serializers.DictField(required=False)

    def validate(self, attrs):
        if attrs.get('action') in ["user.created", "user.updated", "user.deleted"]:
            if 'user_auth_id' not in attrs.get('data', {}):
                raise serializers.ValidationError({"data": "user_auth_id is required."})
        return attrs
