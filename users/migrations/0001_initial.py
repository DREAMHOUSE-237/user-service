from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ProcessedEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('event_id', models.CharField(max_length=128, unique=True)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Utilisateur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('user_auth_id', models.CharField(blank=True, max_length=128, null=True, unique=True)),
                ('email', models.EmailField(unique=True)),
                ('mot_de_passe', models.CharField(max_length=255)),
                ('tel', models.CharField(blank=True, max_length=20, null=True)),
                ('role', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('verification_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('is_identified', models.BooleanField(default=False)),
                ('pending_role', models.CharField(blank=True, default='', max_length=50)),
                ('cni_nom', models.CharField(blank=True, default='', max_length=150)),
                ('cni_prenom', models.CharField(blank=True, default='', max_length=150)),
                ('cni_numero', models.CharField(blank=True, default='', max_length=100)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('utilisateur', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile', to='users.utilisateur',
                )),
                ('username', models.CharField(max_length=150)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='profile_photos/')),
                ('contact', models.CharField(blank=True, max_length=50, null=True)),
                ('email', models.EmailField(blank=True, null=True)),
                ('ville', models.CharField(blank=True, max_length=150, null=True)),
                ('quartier', models.CharField(blank=True, max_length=150, null=True)),
                ('region', models.CharField(blank=True, max_length=50, null=True)),
                ('numeroIdentification', models.CharField(blank=True, max_length=50, null=True)),
                ('nomPDG', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Proprietaire',
            fields=[
                ('utilisateur_ptr', models.OneToOneField(
                    auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True, primary_key=True, serialize=False, to='users.utilisateur',
                )),
                ('nom', models.CharField(max_length=100)),
                ('prenom', models.CharField(max_length=100)),
                ('ville', models.CharField(blank=True, max_length=150, null=True)),
                ('quartier', models.CharField(blank=True, max_length=150, null=True)),
                ('region', models.CharField(blank=True, max_length=50, null=True)),
            ],
            bases=('users.utilisateur',),
        ),
        migrations.CreateModel(
            name='AgenceImmobiliere',
            fields=[
                ('utilisateur_ptr', models.OneToOneField(
                    auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True, primary_key=True, serialize=False, to='users.utilisateur',
                )),
                ('nomAgence', models.CharField(max_length=100)),
                ('ville', models.CharField(blank=True, max_length=150, null=True)),
                ('quartier', models.CharField(blank=True, max_length=150, null=True)),
                ('region', models.CharField(blank=True, max_length=50, null=True)),
                ('numeroIdentification', models.CharField(max_length=50)),
                ('nomPDG', models.CharField(max_length=100)),
                ('contactPrincipal', models.CharField(max_length=50)),
            ],
            options={'verbose_name': 'Agence Immobilière', 'verbose_name_plural': 'Agences Immobilières'},
            bases=('users.utilisateur',),
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('utilisateur_ptr', models.OneToOneField(
                    auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True, primary_key=True, serialize=False, to='users.utilisateur',
                )),
                ('nom', models.CharField(max_length=100)),
                ('prenom', models.CharField(max_length=100)),
                ('ville', models.CharField(blank=True, max_length=150, null=True)),
                ('quartier', models.CharField(blank=True, max_length=150, null=True)),
                ('region', models.CharField(blank=True, max_length=50, null=True)),
            ],
            options={'verbose_name': 'Client', 'verbose_name_plural': 'Clients'},
            bases=('users.utilisateur',),
        ),
        migrations.CreateModel(
            name='Admin',
            fields=[
                ('utilisateur_ptr', models.OneToOneField(
                    auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True, primary_key=True, serialize=False, to='users.utilisateur',
                )),
                ('nom', models.CharField(max_length=100)),
                ('prenom', models.CharField(max_length=100)),
            ],
            options={'verbose_name': 'Admin', 'verbose_name_plural': 'Admins'},
            bases=('users.utilisateur',),
        ),
    ]
