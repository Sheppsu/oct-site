# Generated by Django 4.2.6 on 2024-01-09 23:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tournament", "0031_alter_staticplayer_team"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournamentbracket",
            name="challonge_id",
            field=models.CharField(default="qz54d0uz", max_length=16),
            preserve_default=False,
        ),
    ]
