from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Utilisateur, AgenceImmobiliere, Profile, Proprietaire

class UtilisateurAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            "user_auth_id": "auth-123",
            "email": "test@example.com",
            "mot_de_passe": "password123",
            "tel": "+237600000000",
            "role": "proprietaire"
        }

    def test_create_utilisateur(self):
        response = self.client.post("/users/utilisateurs/", self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Utilisateur.objects.count(), 1)
        self.assertEqual(Utilisateur.objects.get().email, "test@example.com")

    def test_get_utilisateur_list(self):
        Utilisateur.objects.create(**self.user_data)
        response = self.client.get("/users/utilisateurs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_utilisateur(self):
        user = Utilisateur.objects.create(**self.user_data)
        response = self.client.put(f"/users/utilisateurs/{user.id}/", {
            "email": "updated@example.com",
            "mot_de_passe": "password123",
            "tel": "+237600000001",
            "role": "proprietaire",
            "user_auth_id": user.user_auth_id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Utilisateur.objects.get().email, "updated@example.com")

    def test_delete_utilisateur(self):
        user = Utilisateur.objects.create(**self.user_data)
        response = self.client.delete(f"/users/utilisateurs/{user.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Utilisateur.objects.count(), 0)

class ProfileSignalTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_profile_created_for_proprietaire(self):
        p = Proprietaire.objects.create(
        user_auth_id="123",
        nom="Doe",
        prenom="John",
        email="prop@example.com",
        adresse="Bonamoussadi"
    )

        # after creation, profile should exist
        self.assertTrue(hasattr(p, 'profile'))
        self.assertEqual(p.profile.username, "Doe John")
        self.assertEqual(p.profile.utilisateur.email, "prop@example.com")

    def test_profile_created_for_agence(self):
        a = AgenceImmobiliere.objects.create(
            user_auth_id="auth-ag-1",
            email="agence@example.com",
            mot_de_passe="secret",
            tel="+237600000002",
            role="agence",
            nomAgence="ImmoX",
            localisation="Yaounde",
            numeroIdentification="ID123",
            nomPDG="PDG Name",
            contactPrincipal="+237600000003"
        )
        self.assertTrue(hasattr(a, 'profile'))
        self.assertEqual(a.profile.username, "ImmoX")
        self.assertEqual(a.profile.email, "agence@example.com")

    def test_profile_deleted_with_user(self):
        u = Utilisateur.objects.create(
            user_auth_id="auth-user-1",
            email="user@example.com",
            mot_de_passe="secret",
            tel="+237600000004",
            role="client"
        )
        # profile should be created
        self.assertTrue(hasattr(u, 'profile'))
        profile_id = u.profile.id
        # delete user
        u.delete()
        # profile should no longer exist
        self.assertFalse(Profile.objects.filter(id=profile_id).exists())