# Generated by Django 4.2.2 on 2023-08-30 01:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tournament", "0029_tournamentmatch_finished_tournamentmatch_team_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="auth_token",
            field=models.CharField(default=""),
        ),
        migrations.AddField(
            model_name="user",
            name="refresh_at",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
