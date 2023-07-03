from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model, login as _login, logout as _logout
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseServerError, Http404
from django.core.cache import cache

from .models import *

import requests
import traceback
from common import render
from datetime import datetime, timezone


User = get_user_model()
OCT4 = TournamentIteration.objects.get(name="OCT4")


# TODO: maybe move caching logic to models
def get_mappools(tournament: TournamentIteration):
    mps = cache.get(f"{tournament.name}_mappools")
    if mps is None:
        # TODO: multiple brackets is possible
        brackets = tournament.get_brackets()
        if not brackets:
            raise Http404()
        bracket: TournamentBracket = brackets[0]
        # TODO: rounds sharing the same mappool is possible
        rounds = bracket.get_rounds()
        mps = [
            {
                "maps": sorted(rnd.mappool.get_beatmaps(), key=lambda mp: mp.id),
                "stage": rnd.full_name
            } for rnd in reversed(rounds)
        ]
        # TODO: should it be None...?
        cache.set(f"{tournament.name}_mappools", mps, None)
    return mps


def index(req):
    return render(req, "tournament/index.html")


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


def tournaments(req, name=None, section=None):
    if name is None:
        return render(req, "tournament/tournaments.html", {
            "tournaments": TournamentIteration.objects.all()
        })
    name = name.upper()
    tournament = get_object_or_404(TournamentIteration, name=name)
    if section is None:
        return render(req, "tournament/tournament_info.html", {"tournament": tournament})
    try:
        return {
            "mappool": mappools,
            "teams": teams,
            "bracket": bracket,
        }[section](req, name=name)
    except KeyError:
        raise Http404()


def mappools(req, name=None):
    if name is None:
        return redirect("tournament_section", name="OCT4", section="mappool")
    name = name.upper()
    tournament = get_object_or_404(TournamentIteration, name=name)
    return render(req, "tournament/tournament_mappool.html", {
        "mappools": get_mappools(tournament),
        "tournament": tournament,
    })


def teams(req, name=None):
    return render(req, "tournament/tournament_teams.html", {
        "tournament": get_object_or_404(TournamentIteration, name=name.upper())
    })


def bracket(req, name=None):
    return render(req, "tournament/tournament_bracket.html", {
        "tournament": get_object_or_404(TournamentIteration, name=name.upper())
    })


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


def unregister(req):
    if not req.user.is_authenticated:
        return redirect("index")
    involvement = req.user.get_tournament_involvement(tournament_iteration=OCT4)
    if not involvement or UserRoles.REGISTERED_PLAYER not in involvement[0].roles:
        return redirect("index")
    involvement = involvement[0]
    involvement.roles = UserRoles(involvement.roles - UserRoles.REGISTERED_PLAYER)
    involvement.save()
    return redirect("dashboard")
