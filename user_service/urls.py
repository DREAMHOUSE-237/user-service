"""
URL configuration for user_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),  # ✅ inclut toutes les routes de l'app users (profiles, proprietaires, agences, health)
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
