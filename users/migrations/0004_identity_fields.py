from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_utilisateur_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='is_identified',
            field=models.BooleanField(
                default=False,
                help_text='True once the identity service has verified the CNI',
            ),
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='pending_role',
            field=models.CharField(
                blank=True,
                default='',
                max_length=50,
                help_text='Desired role awaiting identity confirmation',
            ),
        ),
    ]
