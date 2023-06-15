from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from common import get_auth_handler


import uuid
from enum import IntFlag, auto
from osu import Client, AuthHandler, GameModeStr


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return UserRoles(value)


class UserManager(BaseUserManager):
    def create_user(self, code):
        # TODO: try statement
        auth: AuthHandler = get_auth_handler()
        auth.get_auth_token(code)
        client = Client(auth)
        user = client.get_own_data(GameModeStr.STANDARD)
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
    roles = UserRolesField(default=0)

    refresh_token = models.CharField(default="")

    USERNAME_FIELD = "osu_username"
    EMAIL_FIELD = None
    REQUIRED_FIELDS = [
        "osu_id",
    ]

    objects = UserManager()

    def __str__(self):
        return self.osu_username
