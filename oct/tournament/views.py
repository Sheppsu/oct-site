from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model, login as _login, logout as _logout
from django.http import HttpResponseBadRequest, HttpResponseServerError, Http404, JsonResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from .serializers import *

import requests
import traceback
from common import render
from datetime import datetime, timezone


User = get_user_model()
OCT4 = TournamentIteration.objects.get(name="OCT4")
USER_DISPLAY_ORDER = [
    UserRoles.HOST,
    UserRoles.REGISTERED_PLAYER,
    UserRoles.MAPPOOLER,
    UserRoles.PLAYTESTER,
    UserRoles.STREAMER,
    UserRoles.COMMENTATOR,
    UserRoles.REFEREE
]


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
        rounds = TournamentRound.objects.select_related("mappool").filter(bracket=bracket)
        mps = [
            {
                "maps": sorted(rnd.mappool.get_beatmaps(), key=lambda mp: mp.id),
                "stage": rnd.full_name
            } for rnd in reversed(rounds)
        ]
        mps = tuple(filter(lambda m: len(m["maps"]) != 0, mps))
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
    roles = sorted(involvement[0].roles.get_roles(), key=lambda r: USER_DISPLAY_ORDER.index(r))
    return render(req, "tournament/dashboard.html", {
        "is_registered": involvement and UserRoles.REGISTERED_PLAYER in involvement[0].roles,
        "roles": ", ".join(map(lambda r: r.name[0]+r.name[1:].replace("_", " ").lower(), roles))
    })


def tournaments(req, name=None, section=None):
    if name is None or name == "":
        return render(req, "tournament/tournaments.html", {
            "tournaments": TournamentIteration.objects.all()
        })
    name = name.upper()
    tournament = get_object_or_404(TournamentIteration, name=name)
    if section is None:
        return render(req, "tournament/tournament_info.html", {
            "tournament": tournament,
            "rounds": [{
                "name": rnd.full_name,
                "date": rnd.str_date
            } for rnd in sorted(tournament.get_brackets()[0].get_rounds(), key=lambda rnd: rnd.start_date)]  # TODO: possible multiple brackets
        })
    try:
        return {
            "mappool": tournament_mappools,
            "teams": tournament_teams,
            "bracket": tournament_bracket,
            "users": tournament_users
        }[section.lower()](req, name=name, tournament=tournament)
    except KeyError:
        raise Http404()


def get_tournament(name, kwargs):
    tournament = kwargs.get("tournament")
    if name is None and tournament is None:
        return
    if tournament is None:
        tournament = get_object_or_404(TournamentIteration, name=name.upper())
    return tournament


def tournament_mappools(req, name=None, round="qualifiers", **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT4", section="mappool")

    if kwargs.get("api"):
        maps = get_object_or_404(TournamentRound, bracket=tournament.get_brackets()[0], name=round.upper()).mappool.get_beatmaps()
        serializer = MappoolBeatmapSerializer(maps, many=True)
        return JsonResponse(serializer.serialize(), safe=False)

    return render(req, "tournament/tournament_mappool.html", {
        "mappools": get_mappools(tournament),
        "tournament": tournament,
    })


@cache_page(60)
def tournament_teams(req, name=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT4", section="teams")
    return render(req, "tournament/tournament_teams.html", {
        "tournament": tournament
    })


@cache_page(60)
def tournament_bracket(req, name=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT4", section="bracket")
    return render(req, "tournament/tournament_bracket.html", {
        "tournament": tournament
    })


@cache_page(60)
def tournament_users(req, name, **kwargs):
    tournament = kwargs.get("tournament") or get_object_or_404(TournamentIteration, name=name.upper())
    involvements = TournamentInvolvement.objects \
        .select_related("user") \
        .filter(tournament_iteration=tournament)

    if kwargs.get("api"):
        serializer = TournamentInvolvementSerializer(involvements, many=True)
        return JsonResponse(serializer.serialize(exclude=["tournament_iteration"]), safe=False)

    users = []
    for enum in USER_DISPLAY_ORDER:
        role = " ".join(map(lambda string: string[0] + string[1:].lower(), enum.name.split("_")))+"s"
        players = sorted(filter(lambda i: enum in i.roles, involvements), key=lambda i: i.join_date)
        users.append({
            "role": role,
            "players": players,
            "count": len(players)
        })
    return render(req, "tournament/tournament_users.html", {
        "tournament": tournament,
        "users": users
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


def referee(req):
    involvement = get_object_or_404(TournamentInvolvement, tournament_iteration=OCT4, user=req.user)
    if UserRoles.REGISTERED_PLAYER in involvement.roles:
        raise Http404()
    return render(req, "tournament/referee.html")
