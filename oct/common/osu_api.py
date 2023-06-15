from osu import AuthHandler, Scope
from django.conf import settings


def get_auth_handler():
    return AuthHandler(settings.OSU_CLIENT_ID, settings.OSU_CLIENT_SECRET, settings.OSU_CLIENT_REDIRECT, Scope.identify())
