# Generated by Django 3.2.16 on 2025-01-14 00:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20250113_0436'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myuser',
            name='username',
            field=models.CharField(max_length=150),
        ),
    ]
