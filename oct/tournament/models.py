from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings

import uuid
from enum import IntFlag, auto
from osu import Client, AuthHandler, GameModeStr, Mods
from common import get_auth_handler


OSU_CLIENT: Client = settings.OSU_CLIENT


class UserRoles(IntFlag):
    # max 15 fields cuz small integer field
    REGISTERED_PLAYER = auto()

    REFEREE = auto()
    STREAMER = auto()
    COMMENTATOR = auto()
    PLAYTESTER = auto()
    MAPPOOLER = auto()

    ADMIN = auto()


class UserRolesField(models.PositiveSmallIntegerField):
    def to_python(self, value):
        return UserRoles(value)


class UserManager(BaseUserManager):
    def create_user(self, code):
        auth: AuthHandler = get_auth_handler()
        try:
            auth.get_auth_token(code)
            client = Client(auth)
            user = client.get_own_data(GameModeStr.STANDARD)
        except:
            return
        try:
            user_obj = User.objects.get(osu_id=user.id)
            user_obj.refresh_token = auth.refresh_token
            user_obj.osu_username = user.username
            user_obj.osu_avatar = user.avatar_url
        except User.DoesNotExist:
            user_obj = User(osu_id=user.id, osu_username=user.username, osu_avatar=user.avatar_url,
                            refresh_token=auth.refresh_token)
        user_obj.save()
        return user_obj


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    osu_id = models.PositiveIntegerField(unique=True, editable=False)
    osu_username = models.CharField(max_length=15, unique=True)
    osu_avatar = models.CharField(default="")

    refresh_token = models.CharField(default="")

    USERNAME_FIELD = "osu_username"
    EMAIL_FIELD = None
    REQUIRED_FIELDS = [
        "osu_id",
    ]

    objects = UserManager()

    def __str__(self):
        return self.osu_username


class TournamentIteration(models.Model):
    name = models.CharField(max_length=16, primary_key=True)
    users = models.ManyToManyField(User, through="TournamentInvolvement")
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


class TournamentInvolvement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tournament_iteration = models.ForeignKey(TournamentIteration, on_delete=models.CASCADE)
    roles = UserRolesField(default=0)
    join_date = models.DateTimeField(blank=True)

    def __str__(self):
        return f"{self.user} {self.tournament_iteration} Involvement"


class TournamentTeam(models.Model):
    team_name = models.CharField(max_length=64)
    players = models.ManyToManyField(User)

    def __str__(self):
        return self.team_name


class TournamentBracket(models.Model):
    # one-to-many relationship in case multiple brackets are used
    # in the future
    tournament_iteration = models.ForeignKey(TournamentIteration, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.tournament_iteration} Bracket"


class TournamentRound(models.Model):
    bracket = models.ForeignKey(TournamentBracket, on_delete=models.CASCADE)
    name = models.CharField(max_length=16)

    def __str__(self):
        return f"{self.bracket.tournament_iteration.name}: {self.name}"


class TournamentMatch(models.Model):
    tournament_round = models.ForeignKey(TournamentRound, on_delete=models.CASCADE)
    match_id = models.PositiveSmallIntegerField()
    teams = models.ManyToManyField(TournamentTeam)
    starting_time = models.DateTimeField()

    def __str__(self):
        return f"{self.tournament_round} Match {self.match_id}"


class Mappool(models.Model):
    tournament_round = models.ForeignKey(TournamentRound, on_delete=models.CASCADE)
    name = models.CharField(max_length=16)

    def __str__(self):
        return f"{self.tournament_round} Mappool"


class MappoolBeatmap(models.Model):
    mappool = models.ForeignKey(Mappool, on_delete=models.CASCADE)
    beatmap_id = models.PositiveSmallIntegerField()
    modification = models.CharField(max_length=4)
    artist = models.CharField()
    title = models.CharField()
    difficulty = models.CharField()
    star_rating = models.FloatField()
    overall_difficulty = models.FloatField()
    approach_rate = models.FloatField()
    circle_size = models.FloatField()
    health_drain = models.FloatField()
    cover = models.CharField()

    @classmethod
    def from_beatmap_id(cls, mappool, modification, beatmap_id):
        beatmap = OSU_CLIENT.get_beatmap(beatmap_id)
        mod = modification[:2]
        beatmap_difficulty = OSU_CLIENT.get_beatmap_attributes(
            beatmap_id,
            mods=Mods.get_from_abbreviation(mod) if mod not in ("NM", "FM", "TB") else None,
            ruleset=GameModeStr.STANDARD
        )
        return cls(
            mappool=mappool,
            beatmap_id=beatmap_id,
            modification=modification,
            artist=beatmap.beatmapset.artist,
            title=beatmap.beatmapset.title,
            difficulty=beatmap.beatmapset.version,
            star_rating=beatmap_difficulty.star_rating,
            overall_difficulty=beatmap.accuracy,
            approach_rate=beatmap.ar,
            circle_size=beatmap.cs,
            health_drain=beatmap.drain,
            background=beatmap.beatmapset.covers.cover_2x
        )

    def __str__(self):
        return f"{self.mappool.tournament_round} {self.modification}"
