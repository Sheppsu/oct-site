# Generated by Django 4.2.2 on 2023-06-15 04:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0002_user_osu_avatar_user_refresh_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='refresh_token',
            field=models.CharField(default=''),
        ),
    ]