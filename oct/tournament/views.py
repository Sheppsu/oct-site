from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model, login as _login, logout as _logout
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseServerError

from .models import TournamentIteration

import requests
import traceback
from common import render
import os
import json


User = get_user_model()


def index(req):
    return render(req, "tournament/index.html")


def teams(req):
    return render(req, "tournament/teams.html")


def mappools(req):
    cur_dir = os.getcwd()
    parent_dir = os.path.abspath(os.path.join(cur_dir, os.pardir))
    file_path = os.path.join(parent_dir, "oct", "static", "testdata", "map_list.json")

    with open (file_path, "r") as f:
        map_list = json.load(f)

    return render(req, "tournament/mappools.html", {"map_list": map_list})


def bracket(req):
    return render(req, "tournament/bracket.html")


def login(req):
    try:
        code = req.GET.get("code", None)
        if code is not None:
            user = User.objects.create_user(code)
            if user is None:
                return HttpResponseServerError()
            _login(req, user, backend=settings.AUTH_BACKEND)
        state = req.GET.get("state", None)
        return redirect(state or "index")
    except requests.HTTPError as exc:
        print(exc)
        return HttpResponseBadRequest()
    except:
        traceback.print_exc()
    return HttpResponseServerError()


def logout(req):
    if req.user.is_authenticated:
        _logout(req.user)
    return redirect("index")


def dashboard(req):
    return redirect("index")


def tournaments(req, name=None):
    if name is None:
        return redirect("named_tournament", name=TournamentIteration.objects.get().name)
    name = name.upper()
    tournament = get_object_or_404(TournamentIteration, name=name)
    return render(req, "tournament/tournaments.html", {"tournament": tournament})
