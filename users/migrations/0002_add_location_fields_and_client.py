# Generated migration — adds region/ville/quartier to all user types,
# replaces adresse/localisation on Proprietaire & AgenceImmobiliere,
# and introduces the Client model.

from django.db import migrations, models
import django.db.models.deletion

REGIONS = [
    ('adamaoua',     'Adamaoua'),
    ('centre',       'Centre'),
    ('est',          'Est'),
    ('extreme_nord', 'Extrême-Nord'),
    ('littoral',     'Littoral'),
    ('nord',         'Nord'),
    ('nord_ouest',   'Nord-Ouest'),
    ('ouest',        'Ouest'),
    ('sud',          'Sud'),
    ('sud_ouest',    'Sud-Ouest'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        # ── Proprietaire ─────────────────────────────────────────────
        migrations.RemoveField(model_name='proprietaire', name='adresse'),
        migrations.AddField(
            model_name='proprietaire',
            name='ville',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='proprietaire',
            name='quartier',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='proprietaire',
            name='region',
            field=models.CharField(blank=True, choices=REGIONS, max_length=50, null=True),
        ),

        # ── AgenceImmobiliere ─────────────────────────────────────────
        migrations.RemoveField(model_name='agenceimmobiliere', name='localisation'),
        migrations.AddField(
            model_name='agenceimmobiliere',
            name='ville',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='agenceimmobiliere',
            name='quartier',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='agenceimmobiliere',
            name='region',
            field=models.CharField(blank=True, choices=REGIONS, max_length=50, null=True),
        ),

        # ── Profile ──────────────────────────────────────────────────
        migrations.RemoveField(model_name='profile', name='adresse'),
        migrations.RemoveField(model_name='profile', name='localisation'),
        migrations.AddField(
            model_name='profile',
            name='ville',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='quartier',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='region',
            field=models.CharField(blank=True, choices=REGIONS, max_length=50, null=True),
        ),

        # ── Client (new model) ────────────────────────────────────────
        migrations.CreateModel(
            name='Client',
            fields=[
                ('utilisateur_ptr', models.OneToOneField(
                    auto_created=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    serialize=False,
                    to='users.utilisateur',
                )),
                ('nom',      models.CharField(max_length=100)),
                ('prenom',   models.CharField(max_length=100)),
                ('ville',    models.CharField(blank=True, max_length=150, null=True)),
                ('quartier', models.CharField(blank=True, max_length=150, null=True)),
                ('region',   models.CharField(blank=True, choices=REGIONS, max_length=50, null=True)),
            ],
            options={
                'verbose_name': 'Client',
                'verbose_name_plural': 'Clients',
            },
            bases=('users.utilisateur',),
        ),
    ]
