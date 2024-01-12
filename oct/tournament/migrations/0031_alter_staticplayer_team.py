# Generated by Django 4.2.6 on 2024-01-08 20:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tournament", "0030_user_auth_token_user_refresh_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="staticplayer",
            name="team",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="players",
                to="tournament.tournamentteam",
            ),
        ),
    ]