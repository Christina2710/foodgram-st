# Generated by Django 3.2.16 on 2025-01-13 00:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_myuser_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myuser',
            name='email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='myuser',
            name='is_subscribed',
            field=models.BooleanField(default=False, verbose_name='Подписка'),
        ),
    ]
