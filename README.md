# user-service

Service de gestion des profils utilisateurs de la plateforme **DREAMHOUSE237**, développé en **Django** (Django REST Framework).

## Rôle

Gère les données de profil métier des utilisateurs, au-delà de l'authentification pure :

- Modèle `Utilisateur` et profils spécialisés par rôle : `Client`, `Proprietaire`, `AgenceImmobiliere`, `Admin` (héritage multi-table Django)
- Informations de localisation (`region`, `ville`, `quartier`)
- Statut de vérification d'identité (`is_identified`, `pending_role`, champs CNI)
- Publication de l'événement `user_created` vers `auth-service` lors de l'inscription
- Publication de l'événement `user-email-queue` vers `publication-service` (email + région, utilisés pour les notifications liées aux biens publiés)

## Stack

- Python 3 / Django / Django REST Framework
- MySQL (AWS RDS, connexion TLS)
- Gunicorn (serveur WSGI, port interne `8000`)
- Pika (client RabbitMQ)

## Flux asynchrone (RabbitMQ)

| Queue | Sens | Déclencheur |
|---|---|---|
| `user_created` | user-service → auth-service | Inscription d'un nouvel utilisateur |
| `user_verified` | consommé par user-service | Confirmation d'email côté auth-service |
| `user_auth_ack` | consommé par user-service | Confirmation de création du compte auth, renseigne `user_auth_id` |
| `user-email-queue` | user-service → publication-service | Email/région pour notifications sur les biens |

## Architecture & découverte de service

S'enregistre auprès de `registry-service` (Eureka) et récupère sa configuration depuis `config-service`. Exposé via `proxy-service` sous le préfixe `/USER-SERVICE/`.

## Variables d'environnement clés

| Variable | Description |
|---|---|
| `DB_SSL_CA` | Certificat CA pour la connexion TLS à RDS |
| `RABBITMQ_USER` / `RABBITMQ_PASSWORD` | Identifiants du broker RabbitMQ |

## Développement local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

⚠️ Les migrations initiales (`0001_initial.py`) doivent refléter exactement `users/models.py`. Avant tout ajout de champ, lancer `python manage.py makemigrations --check --dry-run` pour détecter toute dérive.

## Déploiement

Via **Docker Swarm** (voir [`infrastructure`](https://github.com/DREAMHOUSE-237/infrastructure)). Un push sur `dev` déclenche le pipeline CI/CD complet jusqu'au redéploiement en production.
