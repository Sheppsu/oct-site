from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


import uuid
from enum import IntFlag, auto


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
    pass


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    osu_id = models.PositiveIntegerField(unique=True, editable=False)
    osu_username = models.CharField(max_length=15, unique=True)
    roles = UserRolesField()

    USERNAME_FIELD = "osu_username"
    EMAIL_FIELD = None
    REQUIRED_FIELDS = [
        "osu_id",
    ]

    objects = UserManager()

    def __str__(self):
        return self.osu_username
