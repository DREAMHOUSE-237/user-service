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
from django.core.mail import send_mail
from django.conf import settings

from .models import Utilisateur, Profile, Proprietaire, AgenceImmobiliere, Client, Admin
from .serializers import (
    UtilisateurSerializer, ProfileSerializer,
    ProprietaireSerializer, AgenceImmobiliereSerializer, ClientSerializer, AdminSerializer,
    RegisterProprietaireSerializer, RegisterAgenceSerializer, RegisterClientSerializer,
    RegisterAdminSerializer, AdminValidateCNISerializer,
    REGIONS_DICT,
)
from .services.registration import RegistrationService

logger = logging.getLogger(__name__)

REGISTER_SERIALIZERS = {
    "proprietaire": RegisterProprietaireSerializer,
    "agence":       RegisterAgenceSerializer,
    "client":       RegisterClientSerializer,
    "admin":        RegisterAdminSerializer,
}


# ── Pagination ────────────────────────────────────────────────────────────── #
class StandardPagination(PageNumberPagination):
    page_size            = 20
    page_size_query_param = "page_size"
    max_page_size        = 100


# ── Utility ───────────────────────────────────────────────────────────────── #

def health(request):
    return JsonResponse({"status": "UP"})


def regions(request):
    return JsonResponse(REGIONS_DICT)


# ── Registration ──────────────────────────────────────────────────────────── #

class RegisterView(APIView):
    """
    POST /users/register/
    Register any user type: proprietaire, agence, client, admin.
    Client is NOT required to identify (no CNI needed).
    Admin gets immediate active role.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        role = (request.data.get("role") or "").lower()

        SerializerClass = REGISTER_SERIALIZERS.get(role)
        if not SerializerClass:
            return Response(
                {"error": f"Rôle invalide: '{role}'. Choisir parmi: proprietaire, agence, client, admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SerializerClass(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data         = serializer.validated_data
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

        user.is_verified       = True
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


# ── Admin: User Management ────────────────────────────────────────────────── #

class AdminUserListView(APIView):
    """
    GET /users/admin/users/
    Admin can list all users (all roles).
    Optional filters: ?role=proprietaire&is_identified=false&is_verified=true
    """
    permission_classes = [AllowAny]  # In production: restrict to admin token

    def get(self, request):
        qs = Utilisateur.objects.all().order_by('-date_creation')

        role_filter         = request.query_params.get('role')
        is_identified_filter = request.query_params.get('is_identified')
        is_verified_filter  = request.query_params.get('is_verified')

        if role_filter:
            qs = qs.filter(role=role_filter)
        if is_identified_filter is not None:
            qs = qs.filter(is_identified=(is_identified_filter.lower() == 'true'))
        if is_verified_filter is not None:
            qs = qs.filter(is_verified=(is_verified_filter.lower() == 'true'))

        paginator = StandardPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(UtilisateurSerializer(page, many=True).data)


class AdminUserDetailView(APIView):
    """
    GET  /users/admin/users/<id>/  — View user details
    PUT  /users/admin/users/<id>/  — Update user (role, is_active, etc.)
    DELETE /users/admin/users/<id>/ — Delete user
    """
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            user = Utilisateur.objects.get(pk=user_id)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé."}, status=404)
        return Response(UtilisateurSerializer(user).data)

    def put(self, request, user_id):
        try:
            user = Utilisateur.objects.get(pk=user_id)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé."}, status=404)

        # Admin can update: role, is_active, tel
        allowed_fields = ['role', 'is_active', 'tel']
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response(UtilisateurSerializer(user).data)

    def delete(self, request, user_id):
        try:
            user = Utilisateur.objects.get(pk=user_id)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé."}, status=404)
        email = user.email
        user.delete()
        return Response({"message": f"Utilisateur {email} supprimé."})


class AdminPendingUsersView(APIView):
    """
    GET /users/admin/pending/
    List all users still waiting for identity verification (pending_proprietaire, pending_agence).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        pending = Utilisateur.objects.filter(
            role__in=['pending_proprietaire', 'pending_agence']
        ).order_by('date_creation')
        paginator = StandardPagination()
        page      = paginator.paginate_queryset(pending, request)
        return paginator.get_paginated_response(UtilisateurSerializer(page, many=True).data)


class AdminValidateCNIView(APIView):
    """
    POST /users/admin/validate-cni/
    Admin manually validates (or rejects) a user whose OCR failed.
    Admin must enter: user_id, nom, prenom, numero_cni, action.

    Body:
    {
        "user_id": 42,
        "action": "approve",
        "nom": "KAMGA",
        "prenom": "Jean-Paul",
        "numero_cni": "123456789"
    }
    OR
    {
        "user_id": 42,
        "action": "reject",
        "rejection_reason": "Document illisible"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminValidateCNISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data    = serializer.validated_data
        user_id = data['user_id']
        action  = data['action']

        try:
            user = Utilisateur.objects.get(pk=user_id)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé."}, status=404)

        if user.role not in ('pending_proprietaire', 'pending_agence'):
            return Response(
                {"error": f"L'utilisateur a le rôle '{user.role}', pas de validation CNI en attente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == 'approve':
            # Determine final role from pending_role or current role
            final_role = user.pending_role or user.role.replace('pending_', '')
            user.role          = final_role
            user.is_identified = True
            user.pending_role  = ''
            user.cni_nom       = data['nom']
            user.cni_prenom    = data['prenom']
            user.cni_numero    = data['numero_cni']
            user.save(update_fields=['role', 'is_identified', 'pending_role', 'cni_nom', 'cni_prenom', 'cni_numero'])

            self._send_approval_email(user, final_role)
            logger.info("[admin] Manually approved user %s → role=%s", user.email, final_role)

            return Response({
                "message":     f"Utilisateur {user.email} validé. Rôle → {final_role}.",
                "user_id":     user.pk,
                "email":       user.email,
                "role":        user.role,
                "nom":         user.cni_nom,
                "prenom":      user.cni_prenom,
                "numero_cni":  user.cni_numero,
            })
        else:
            # Reject
            user.is_identified = False
            user.save(update_fields=['is_identified'])
            rejection_reason   = data.get('rejection_reason', '')
            self._send_rejection_email(user, rejection_reason)
            logger.info("[admin] Manually rejected user %s", user.email)

            return Response({
                "message":          f"Utilisateur {user.email} rejeté.",
                "user_id":          user.pk,
                "email":            user.email,
                "rejection_reason": rejection_reason,
            })

    def _send_approval_email(self, user, role):
        label = {'proprietaire': 'Propriétaire', 'agence': 'Agence Immobilière'}.get(role, role)
        try:
            send_mail(
                subject="DreamHouse237 — Identité vérifiée ✓",
                message=(
                    f"Bonjour,\n\n"
                    f"Votre identité a été vérifiée par notre équipe. "
                    f"Votre compte est maintenant actif en tant que {label}.\n\n"
                    f"L'équipe DreamHouse237"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning("Could not send approval email: %s", exc)

    def _send_rejection_email(self, user, reason):
        try:
            send_mail(
                subject="DreamHouse237 — Vérification d'identité refusée",
                message=(
                    f"Bonjour,\n\n"
                    f"Nous n'avons pas pu vérifier votre identité.\n"
                    f"Raison : {reason or 'Document non lisible ou invalide.'}\n\n"
                    f"Contactez le support pour resoumettre votre CNI.\n\n"
                    f"L'équipe DreamHouse237"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning("Could not send rejection email: %s", exc)


# ── ViewSets avec pagination ──────────────────────────────────────────────── #

class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset         = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    pagination_class = StandardPagination

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
    pagination_class = StandardPagination

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
    pagination_class = StandardPagination


class AgenceImmobiliereViewSet(viewsets.ModelViewSet):
    queryset         = AgenceImmobiliere.objects.all()
    serializer_class = AgenceImmobiliereSerializer
    pagination_class = StandardPagination


class ClientViewSet(viewsets.ModelViewSet):
    queryset         = Client.objects.all()
    serializer_class = ClientSerializer
    pagination_class = StandardPagination


class AdminViewSet(viewsets.ModelViewSet):
    queryset         = Admin.objects.all()
    serializer_class = AdminSerializer
    pagination_class = StandardPagination
