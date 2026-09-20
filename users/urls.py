from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UtilisateurViewSet, ProfileViewSet,
    ProprietaireViewSet, AgenceImmobiliereViewSet, ClientViewSet, AdminViewSet,
    RegisterView, VerifyEmailView, ResendVerificationView,
    AdminUserListView, AdminUserDetailView, AdminPendingUsersView, AdminValidateCNIView,
    UpdateUserView,
    health, regions,
)

router = DefaultRouter()
router.register(r'users',         UtilisateurViewSet)
router.register(r'profiles',      ProfileViewSet)
router.register(r'proprietaires', ProprietaireViewSet)
router.register(r'agences',       AgenceImmobiliereViewSet)
router.register(r'clients',       ClientViewSet)
router.register(r'admins',        AdminViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # ── Auth / registration ───────────────────────────────────────
    path('register/',                          RegisterView.as_view(),           name='register'),
    path('verify-email/<uuid:token>/',         VerifyEmailView.as_view(),        name='verify-email'),
    path('resend-verification/',               ResendVerificationView.as_view(), name='resend-verification'),

    # ── Admin: user management ────────────────────────────────────
    path('admin/users/',                       AdminUserListView.as_view(),      name='admin-user-list'),
    path('admin/users/<int:user_id>/',         AdminUserDetailView.as_view(),    name='admin-user-detail'),
    path('admin/pending/',                     AdminPendingUsersView.as_view(),  name='admin-pending-users'),
    path('admin/validate-cni/',                AdminValidateCNIView.as_view(),   name='admin-validate-cni'),

    # ── Modification des informations personnelles ────────────────────
    path('user/<pk>/modification/',            UpdateUserView.as_view(),         name='user-modification'),

    # ── Utility ───────────────────────────────────────────────────
    path('health',    health),
    path('regions/',  regions),
]
