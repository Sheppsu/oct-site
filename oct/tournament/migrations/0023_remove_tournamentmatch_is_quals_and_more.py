# Generated by Django 4.2.2 on 2023-07-23 06:24

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tournament", "0022_staticplayer_is_captain_staticplayer_tier_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="tournamentmatch",
            name="is_quals",
        ),
        migrations.RemoveField(
            model_name="tournamentround",
            name="ban_order",
        ),
    ]
