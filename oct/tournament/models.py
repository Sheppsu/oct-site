from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings

import uuid
from enum import IntFlag, IntEnum, auto
from osu import Client, AuthHandler, GameModeStr, Mods
from datetime import datetime, timezone
from time import time

from common import get_auth_handler, enum_field, date_to_string


OSU_CLIENT: Client = settings.OSU_CLIENT
ROUNDS_ORDER = ("QUALIFIERS", "RO128", "RO64", "RO32", "RO16", "QF", "SF", "FINALS", "GF")


def ar_to_ms(ar):
    return 1200 + (750 if ar >= 5 else 600) * (5 - ar) / 5


def ms_to_ar(ms):
    return 5 - (ms - 1200) / (750 if ms <= 1200 else 600) * 5


def od_to_ms(od):
    return 80 - 6 * od


def ms_to_od(ms):
    return (80 - ms) / 6


def calculate_modded_stats(ar, od, cs, hp, mods):
    if "HR" in mods:
        ar = min(ar * 1.4, 10)
        od = min(od * 1.4, 10)
        cs = min(cs * 1.3, 10)
        hp = min(hp * 1.4, 10)
    elif "EZ" in mods:
        ar *= 0.5
        od *= 0.5
        cs *= 0.5
        hp *= 0.5

    if "DT" in mods:
        ar = ms_to_ar(ar_to_ms(ar)*2/3)
        od = ms_to_od(od_to_ms(od)*2/3)
    elif "HT" in mods:
        ar = ms_to_ar(ar_to_ms(ar)*4/3)
        od = ms_to_od(od_to_ms(od)*4/3)

    return ar, od, cs, hp


class UserRoles(IntFlag):
    # max 15 fields cuz small integer field
    REGISTERED_PLAYER = auto()
    REFEREE = auto()
    STREAMER = auto()
    COMMENTATOR = auto()
    PLAYTESTER = auto()
    MAPPOOLER = auto()
    HOST = auto()
    CUSTOM_MAPPER = auto()

    def get_roles(self):
        count = 1
        value = self.value
        while count <= value:
            if count & value:
                yield UserRoles(count)
            count <<= 1


class BracketType(IntEnum):
    DOUBLE_ELIMINATION = 0


@enum_field(UserRoles, models.PositiveSmallIntegerField)
class UserRolesField:
    pass


@enum_field(BracketType, models.PositiveSmallIntegerField)
class BracketTypeField:
    pass


class UserManager(BaseUserManager):
    def create_user(self, code):
        auth: AuthHandler = get_auth_handler()
        auth.get_auth_token(code)
        client = Client(auth)
        user = client.get_own_data(GameModeStr.STANDARD)
        try:
            user_obj = User.objects.get(osu_id=user.id)
            user_obj.refresh_token = auth.refresh_token
            user_obj.osu_username = user.username
            user_obj.osu_avatar = user.avatar_url
            user_obj.osu_cover = user.cover.url
        except User.DoesNotExist:
            user_obj = User(osu_id=user.id, osu_username=user.username, osu_avatar=user.avatar_url, osu_cover=user.cover.url,
                            refresh_token=auth.refresh_token)
        user_obj.save()
        return user_obj


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    osu_id = models.PositiveIntegerField(unique=True, editable=False)
    osu_username = models.CharField(max_length=15, unique=True)
    osu_avatar = models.CharField(default="")
    osu_cover = models.CharField(default="")

    auth_token = models.CharField(default="")
    refresh_token = models.CharField(default="")
    refresh_at = models.PositiveIntegerField(default=0)

    is_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "osu_username"
    EMAIL_FIELD = None
    REQUIRED_FIELDS = [
        "osu_id",
    ]

    objects = UserManager()

    def get_auth_handler(self):
        auth: AuthHandler = get_auth_handler()
        now = time()
        if self.refresh_at < now:
            auth.refresh_access_token(self.refresh_token)
            self.refresh_token = auth.refresh_token
            self.refresh_at = now+600
            self.auth_token = auth.token
            self.save()
        else:
            auth._token = self.auth_token
            auth.expire_time = time()
        return auth

    def get_tournament_involvement(self, **kwargs):
        return TournamentInvolvement.objects.filter(user=self, **kwargs)

    def __str__(self):
        return self.osu_username


class TournamentIteration(models.Model):
    name = models.CharField(max_length=8, primary_key=True)
    full_name = models.CharField(max_length=32)
    users = models.ManyToManyField(User, through="TournamentInvolvement")
    start_date = models.DateField()
    end_date = models.DateField()
    thumbnail = models.CharField(max_length=32)
    links = models.JSONField(default=list)

    def get_brackets(self, **kwargs):
        return TournamentBracket.objects.filter(tournament_iteration=self, **kwargs)

    def __str__(self):
        return self.name

    @property
    def date_span(self):
        return f"{date_to_string(self.start_date)} - {date_to_string(self.end_date)}"


class TournamentInvolvement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tournament_iteration = models.ForeignKey(TournamentIteration, on_delete=models.CASCADE)
    roles = UserRolesField(default=0)
    join_date = models.DateTimeField(null=True)

    def __str__(self):
        return str(self.roles)


class TournamentBracket(models.Model):
    # one-to-many relationship in case multiple brackets are used
    # in the future
    tournament_iteration = models.ForeignKey(TournamentIteration, on_delete=models.CASCADE)
    type = BracketTypeField(default=BracketType.DOUBLE_ELIMINATION)
    challonge_id = models.CharField(max_length=16)

    def get_rounds(self, **kwargs):
        return TournamentRound.objects.filter(bracket=self, **kwargs)

    def __str__(self):
        return self.type.name


class TournamentTeam(models.Model):
    bracket = models.ForeignKey(TournamentBracket, on_delete=models.RESTRICT)
    name = models.CharField(max_length=64)
    icon = models.CharField(max_length=64, null=True)
    seed = models.PositiveSmallIntegerField(null=True)

    def get_players_with_user(self):
        return StaticPlayer.objects.select_related("user").filter(team=self)

    def __str__(self):
        return self.name


class StaticPlayer(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    team = models.ForeignKey(TournamentTeam, on_delete=models.CASCADE, related_name="players")
    osu_rank = models.PositiveIntegerField()
    is_captain = models.BooleanField(default=False)
    tier = models.CharField(max_length=1, null=True)


class Mappool(models.Model):
    mappack = models.CharField(default="")

    def get_rounds(self, **kwargs):
        return TournamentRound.objects.filter(mappool=self, **kwargs)

    def get_beatmaps(self, **kwargs):
        return MappoolBeatmap.objects.filter(mappool=self, **kwargs)


class TournamentRound(models.Model):
    bracket = models.ForeignKey(TournamentBracket, on_delete=models.CASCADE)
    mappool = models.ForeignKey(Mappool, on_delete=models.RESTRICT)
    name = models.CharField(max_length=16)
    full_name = models.CharField(max_length=32)
    start_date = models.DateField()

    def get_matches(self, **kwargs):
        return TournamentMatch.objects.filter(tournament_round=self, **kwargs)

    def __str__(self):
        return self.full_name

    @property
    def str_date(self):
        return date_to_string(self.start_date)

    def __lt__(self, other):
        return ROUNDS_ORDER.index(self.name) < ROUNDS_ORDER.index(other.name)

    def __gt__(self, other):
        return ROUNDS_ORDER.index(self.name) > ROUNDS_ORDER.index(other.name)


class TournamentMatch(models.Model):
    tournament_round = models.ForeignKey(TournamentRound, on_delete=models.CASCADE)
    match_id = models.PositiveSmallIntegerField()
    teams = models.ManyToManyField(TournamentTeam)
    team_order = models.CharField(default="")
    starting_time = models.DateTimeField(null=True)
    is_losers = models.BooleanField(default=False)
    osu_match_id = models.PositiveIntegerField(null=True)

    bans = models.CharField(max_length=32, null=True)
    picks = models.CharField(max_length=64, null=True)
    wins = models.CharField(max_length=16, null=True)
    finished = models.BooleanField(default=False)

    referee = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, related_name="+")
    streamer = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, related_name="+")
    commentator1 = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, related_name="+")
    commentator2 = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, related_name="+")

    @property
    def time_str(self):
        return self.starting_time.strftime("%m/%d %H:%M (%Z)") \
            if self.starting_time else "Not scheduled"

    @property
    def winner(self):
        return round(self.wins.count("2")/len(self.wins)) if self.finished else None
        
    def get_has_started(self):
        return datetime.now(tz=timezone.utc) > self.starting_time

    def get_progress(self):
        return "UPCOMING" if self.starting_time is None or not self.get_has_started()\
                          else ("ONGOING" if not self.finished else "FINISHED")

    def get_match_info(self):
        if self.osu_match_id is None:
            return
        return OSU_CLIENT.get_match(self.osu_match_id)

    def add_team(self, team: TournamentTeam):
        self.teams.add(team)
        self.team_order += ("," if self.team_order else "") + str(team.id)
        self.save()

    def remove_team(self, team: TournamentTeam):
        self.teams.remove(team)
        team_order = self.team_order.split(",")
        team_order.remove(str(team.id))
        self.team_order = ",".join(team_order)

    def __str__(self):
        return str(self.match_id)

    def __gt__(self, other):
        if self.tournament_round_id == other.tournament_round_id:
            if self.starting_time is None or other.starting_time is None:
                return self.match_id > other.match_id
            elif (has_started:=self.get_has_started()) == other.get_has_started():
                return self.starting_time > other.starting_time if not has_started else self.starting_time < other.starting_time
            return has_started
        return ROUNDS_ORDER.index(self.tournament_round.name) < ROUNDS_ORDER.index(other.tournament_round.name)

    def __lt__(self, other):
        return not self.__gt__(other)


class MappoolBeatmap(models.Model):
    mappool = models.ForeignKey(Mappool, on_delete=models.CASCADE)
    beatmap_id = models.PositiveIntegerField()
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.color = {
            "NM": "#52a1ff",
            "HD": "#ffe599",
            "HR": "#ea9999",
            "DT": "#b4a7d6",
            "FM": "#50f6fc",
            "EZ": "#99ea99",
            "TB": "#d5a6bd"
        }[self.modification[:2]]
        self.cs_percent = str(self.circle_size * 10)+"%"
        self.ar_percent = str(round(
            self.approach_rate / (11 if self.modification.startswith("DT") else 10) * 100, 1
        ))+"%"
        self.od_percent = str(round(
            self.overall_difficulty / (11 if self.modification.startswith("DT") else 10) * 100, 1
        ))+"%"
        self.hp_percent = str(self.health_drain * 10)+"%"
        self.rounded_sr = round(self.star_rating, 2)

    @property
    def rounded_ar(self):
        return round(self.approach_rate, 1)

    @property
    def rounded_od(self):
        return round(self.overall_difficulty, 1)

    @property
    def rounded_cs(self):
        return round(self.circle_size, 1)

    @property
    def rounded_hp(self):
        return round(self.health_drain, 1)

    @classmethod
    def from_beatmap_id(cls, mappool: Mappool, modification: str, beatmap_id: int):
        modification = modification.upper()
        beatmap = OSU_CLIENT.get_beatmap(beatmap_id)
        mod = modification[:2]
        beatmap_difficulty = OSU_CLIENT.get_beatmap_attributes(
            beatmap_id,
            mods=Mods.get_from_abbreviation(mod) if mod not in ("NM", "FM", "TB") else None,
            ruleset=GameModeStr.STANDARD
        )
        ar, od, cs, hp = calculate_modded_stats(beatmap.ar, beatmap.accuracy, beatmap.cs, beatmap.drain, mod)
            
        return cls(
            mappool=mappool,
            beatmap_id=beatmap_id,
            modification=modification,
            artist=beatmap.beatmapset.artist,
            title=beatmap.beatmapset.title,
            difficulty=beatmap.version,
            star_rating=beatmap_difficulty.star_rating,
            overall_difficulty=od,
            approach_rate=ar,
            circle_size=cs,
            health_drain=hp,
            cover=beatmap.beatmapset.covers.cover_2x
        )

    def __str__(self):
        return self.modification
