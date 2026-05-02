from django.contrib import admin
from .models import Utilisateur, Proprietaire, AgenceImmobiliere, Client, Profile, ProcessedEvent


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'role', 'is_active', 'date_creation')
    search_fields = ('email', 'user_auth_id', 'role')


@admin.register(Proprietaire)
class ProprietaireAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'nom', 'prenom', 'region', 'ville', 'quartier', 'user_auth_id')
    search_fields = ('email', 'nom', 'prenom')
    list_filter = ('region',)


@admin.register(AgenceImmobiliere)
class AgenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'nomAgence', 'region', 'ville', 'quartier', 'user_auth_id')
    search_fields = ('email', 'nomAgence')
    list_filter = ('region',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'nom', 'prenom', 'region', 'ville', 'quartier', 'user_auth_id')
    search_fields = ('email', 'nom', 'prenom')
    list_filter = ('region',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'contact', 'region', 'ville', 'quartier', 'utilisateur')
    list_filter = ('region',)
    search_fields = ('username', 'email')


@admin.register(ProcessedEvent)
class ProcessedEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'processed_at')
