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
