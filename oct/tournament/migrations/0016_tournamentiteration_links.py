# Generated by Django 4.2.2 on 2023-07-07 06:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0015_tournamentround_start_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentiteration',
            name='links',
            field=models.JSONField(default="{}"),
            preserve_default=True,
        ),
    ]
