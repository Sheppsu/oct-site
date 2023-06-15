from django.shortcuts import render as _render
from django.conf import settings


def render(req, template, context=None, *args, **kwargs):
    if context is None:
        context = {}
    context["login_url"] = settings.OSU_AUTH_URL+f"&state={req.path}"
    context["is_logged_in"] = req.user.is_authenticated
    if req.user.is_authenticated:
        context["avatar_url"] = req.user.osu_avatar
        context["username"] = req.user.osu_username
    return _render(req, template, context, *args, **kwargs)
