from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model, login as _login, logout as _logout
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.core.cache import cache

from .models import *

import requests
import traceback
from common import render
from datetime import datetime, timezone


User = get_user_model()
OCT4 = TournamentIteration.objects.get(name="OCT4")


def get_mappools(name):
    mps = cache.get(f"{name}_mappools")
    if mps is None:
        tournament: TournamentIteration = get_object_or_404(TournamentIteration, name=name)
        # TODO: multiple brackets is possible
        bracket: TournamentBracket = tournament.get_brackets()[0]
        # TODO: rounds sharing the same mappool is possible
        rounds = bracket.get_rounds()
        mps = [{"maps": rnd.mappool.get_beatmaps(), "stage": rnd.full_name} for rnd in reversed(rounds)]
        # TODO: should it be None...?
        cache.set(f"{name}_mappools", mps, None)
    return mps


def index(req):
    return render(req, "tournament/index.html")


def teams(req):
    return render(req, "tournament/teams.html")


def mappools(req, name=None):
    if name is None:
        return redirect("named_mappools", name=TournamentIteration.objects.get().name)
    return render(req, "tournament/mappools.html", {
        "mappools": get_mappools(name.upper())
    })


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
        _logout(req)
    return redirect("index")


def dashboard(req):
    if not req.user.is_authenticated:
        return redirect("index")
    involvement = req.user.get_tournament_involvement(tournament_iteration=OCT4)
    return render(req, "tournament/dashboard.html", {
        "is_registered": involvement and UserRoles.REGISTERED_PLAYER in involvement[0].roles
    })


def tournaments(req, name=None):
    if name is None:
        return render(req, "tournament/tournaments.html", {
            "tournaments": list(TournamentIteration.objects.all())*6
        })
    name = name.upper()
    tournament = get_object_or_404(TournamentIteration, name=name)
    return render(req, "tournament/tournament.html", {"tournament": tournament})


def register(req):
    if not req.user.is_authenticated:
        return redirect("index")
    involvement = req.user.get_tournament_involvement(tournament_iteration=OCT4)
    if not involvement:
        TournamentInvolvement.objects.create(
            user=req.user,
            tournament_iteration=OCT4,
            roles=UserRoles.REGISTERED_PLAYER,
            join_date=datetime.now(timezone.utc)
        ).save()
        return redirect("dashboard")
    involvement = involvement[0]
    if UserRoles.REGISTERED_PLAYER in involvement.roles:
        return redirect("index")
    involvement.roles |= UserRoles.REGISTERED_PLAYER
    involvement.save()
    return redirect("dashboard")
