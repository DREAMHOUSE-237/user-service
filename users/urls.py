from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UtilisateurViewSet, ProfileViewSet,
    ProprietaireViewSet, AgenceImmobiliereViewSet, ClientViewSet,
    RegisterView, VerifyEmailView, ResendVerificationView,
    health, regions,
)

router = DefaultRouter()
router.register(r'users',         UtilisateurViewSet)
router.register(r'profiles',      ProfileViewSet)
router.register(r'proprietaires', ProprietaireViewSet)
router.register(r'agences',       AgenceImmobiliereViewSet)
router.register(r'clients',       ClientViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # ── Auth / registration ───────────────────────────────────────
    path('register/',                          RegisterView.as_view(),          name='register'),
    path('verify-email/<uuid:token>/',         VerifyEmailView.as_view(),       name='verify-email'),
    path('resend-verification/',               ResendVerificationView.as_view(), name='resend-verification'),

    # ── Utility ───────────────────────────────────────────────────
    path('health',    health),
    path('regions/',  regions),
]
