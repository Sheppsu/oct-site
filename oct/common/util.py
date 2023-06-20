from django.shortcuts import render as _render
from django.conf import settings


def render(req, template, context=None, *args, **kwargs):
    if context is None:
        context = {}
    context["login_url"] = settings.OSU_AUTH_URL+f"&state={req.path}"
    context["is_logged_in"] = req.user.is_authenticated
    if req.user.is_authenticated:
        context["avatar_url"] = req.user.osu_avatar
        username = req.user.osu_username
        context["username"] = username
        context["short_username"] = username if len(username) < 9 else username[:7]+"..."
    return _render(req, template, context, *args, **kwargs)


def enum_field(enum, field):
    def decorator(cls):
        return type(
            cls.__name__,
            (cls, field,),
            {
                "from_db_value": lambda self, value, expression, connection: enum(value),
                "to_python": lambda self, value: value if isinstance(value, enum) else enum(value),
                "get_prep_value": lambda self, value: value.value if isinstance(value, enum) else value
            }
        )
    return decorator
