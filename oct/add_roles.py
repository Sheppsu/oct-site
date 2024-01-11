import django
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["DJANGO_SETTINGS_MODULE"] = "oct.settings"
django.setup()


from tournament.models import *
from datetime import datetime, timezone


oct5 = TournamentIteration.objects.get(name="OCT5")


def add_roles(users, role):
    for u in users:
        print(u)
        user = User.objects.get(**{("osu_username" if type(u) == str else "osu_id"): u})
        i, created = TournamentInvolvement.objects.get_or_create(
            user=user, 
            tournament_iteration=oct5, 
            defaults={
                "roles": role,
                "join_date": datetime.now(tz=timezone.utc)
            }
        )
        if not created:
            i.roles |= role
            i.save()


if __name__ == "__main__":
    users = [14895608, "Among Us", "shushio", "cloudsiqh", "Lightin", "YesRooster"]
    role = UserRoles.REFEREE
    add_roles(users, role)
