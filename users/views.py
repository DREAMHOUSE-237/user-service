# users/views.py
import logging
import uuid

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from django.http import JsonResponse

from .models import Utilisateur, Profile, Proprietaire, AgenceImmobiliere, Client
from .serializers import (
    UtilisateurSerializer, ProfileSerializer,
    ProprietaireSerializer, AgenceImmobiliereSerializer, ClientSerializer,
    RegisterProprietaireSerializer, RegisterAgenceSerializer, RegisterClientSerializer,
    REGIONS_DICT,
)
from .services.registration import RegistrationService

logger = logging.getLogger(__name__)

REGISTER_SERIALIZERS = {
    "proprietaire": RegisterProprietaireSerializer,
    "agence":       RegisterAgenceSerializer,
    "client":       RegisterClientSerializer,
}


# ── Pagination ────────────────────────────────────────────────────────────── #
class StandardPagination(PageNumberPagination):
    """
    CORRECTION : sans pagination, .objects.all() charge TOUTE la table en RAM.
    Avec 10 000 users → plusieurs centaines de MB perdus en mémoire.
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ── Utility ───────────────────────────────────────────────────────────────── #

def health(request):
    return JsonResponse({"status": "UP"})


def regions(request):
    return JsonResponse(REGIONS_DICT)


# ── Registration ──────────────────────────────────────────────────────────── #

class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        role = (request.data.get("role") or "").lower()

        SerializerClass = REGISTER_SERIALIZERS.get(role)
        if not SerializerClass:
            return Response(
                {"error": f"Rôle invalide: '{role}'. Choisir parmi: proprietaire, agence, client."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SerializerClass(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        raw_password = data.pop("password")

        service = RegistrationService()
        try:
            user = service.register(role=role, raw_password=raw_password, **data)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error during registration")
            return Response(
                {"error": "Erreur interne du serveur."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message":     "Compte créé. Vérifiez votre email pour activer votre compte.",
                "email":       user.email,
                "role":        user.role,
                "is_verified": user.is_verified,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Email verification ────────────────────────────────────────────────────── #

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = Utilisateur.objects.get(verification_token=token)
        except Utilisateur.DoesNotExist:
            return Response(
                {"error": "Lien de vérification invalide ou déjà utilisé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_verified:
            return Response({"message": "Compte déjà vérifié."}, status=status.HTTP_200_OK)

        user.is_verified = True
        user.verification_token = uuid.uuid4()
        user.save(update_fields=["is_verified", "verification_token"])

        try:
            from .utils.rabbit_publisher import publish_message
            publish_message("user_verified", {
                "email":           user.email,
                "user_service_id": user.pk,
                "user_auth_id":    user.user_auth_id,
            })
        except Exception as exc:
            logger.warning("Could not publish user_verified event: %s", exc)

        return Response(
            {"message": "Compte vérifié avec succès. Vous pouvez maintenant vous connecter."},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "email requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Utilisateur.objects.get(email=email)
        except Utilisateur.DoesNotExist:
            return Response(
                {"message": "Si cet email est enregistré et non vérifié, un lien vous a été envoyé."},
                status=status.HTTP_200_OK,
            )

        if user.is_verified:
            return Response({"message": "Ce compte est déjà vérifié."}, status=status.HTTP_200_OK)

        service = RegistrationService()
        try:
            service._send_verification_email(user)
        except Exception:
            logger.exception("Could not resend verification email")
            return Response(
                {"error": "Impossible d'envoyer l'email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Si cet email est enregistré et non vérifié, un lien vous a été envoyé."},
            status=status.HTTP_200_OK,
        )


# ── ViewSets avec pagination ──────────────────────────────────────────────── #

class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset           = Utilisateur.objects.all()
    serializer_class   = UtilisateurSerializer
    pagination_class   = StandardPagination           # ← CORRECTION

    @action(detail=True, methods=["get"])
    def profile(self, request, pk=None):
        user = self.get_object()
        if hasattr(user, "profile"):
            return Response(ProfileSerializer(user.profile, context={"request": request}).data)
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"], url_path="attr/(?P<field>[^/.]+)")
    def get_attr(self, request, pk=None, field=None):
        user = self.get_object()
        if hasattr(user, field):
            return Response({field: getattr(user, field)})
        return Response({"detail": f"Attribute '{field}' not found."}, status=404)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset         = Profile.objects.select_related("utilisateur").all()
    serializer_class = ProfileSerializer
    parser_classes   = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardPagination             # ← CORRECTION

    @action(
        detail=True, methods=["patch"], url_path="upload-photo",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_photo(self, request, pk=None):
        profile = self.get_object()
        photo   = request.FILES.get("photo")
        if not photo:
            return Response({"detail": "No photo provided."}, status=status.HTTP_400_BAD_REQUEST)
        profile.photo = photo
        profile.save()
        return Response(ProfileSerializer(profile, context={"request": request}).data)


class ProprietaireViewSet(viewsets.ModelViewSet):
    queryset         = Proprietaire.objects.all()
    serializer_class = ProprietaireSerializer
    pagination_class = StandardPagination             # ← CORRECTION


class AgenceImmobiliereViewSet(viewsets.ModelViewSet):
    queryset         = AgenceImmobiliere.objects.all()
    serializer_class = AgenceImmobiliereSerializer
    pagination_class = StandardPagination             # ← CORRECTION


class ClientViewSet(viewsets.ModelViewSet):
    queryset         = Client.objects.all()
    serializer_class = ClientSerializer
    pagination_class = StandardPagination             # ← CORRECTION