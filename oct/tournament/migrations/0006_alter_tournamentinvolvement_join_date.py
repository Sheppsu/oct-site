# Generated by Django 4.2.2 on 2023-06-17 07:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0005_mappool_tournamentbracket_tournamentinvolvement_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournamentinvolvement',
            name='join_date',
            field=models.DateTimeField(null=True),
        ),
    ]