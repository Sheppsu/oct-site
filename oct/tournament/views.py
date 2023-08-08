from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model, login as _login, logout as _logout
from django.http import HttpResponseBadRequest, HttpResponseServerError, Http404, JsonResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from .serializers import *

import requests
import traceback
import sys
from common import render
from datetime import datetime, timezone


User = get_user_model()
OCT4 = TournamentIteration.objects.get(name="OCT4")
USER_DISPLAY_ORDER = [
    UserRoles.HOST,
    UserRoles.REGISTERED_PLAYER,
    UserRoles.CUSTOM_MAPPER,
    UserRoles.MAPPOOLER,
    UserRoles.PLAYTESTER,
    UserRoles.STREAMER,
    UserRoles.COMMENTATOR,
    UserRoles.REFEREE
]


def error_500(request):
    return render(request, "tournament/error_500.html")

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
    roles = sorted(involvement[0].roles.get_roles(), key=lambda r: USER_DISPLAY_ORDER.index(r)) \
        if involvement else None
    formatted_roles = ", ".join(map(lambda r: r.name[0]+r.name[1:].replace("_", " ").lower(), roles)) \
        if roles else "No Roles"

    context = {
        "is_registered": involvement and UserRoles.REGISTERED_PLAYER in involvement[0].roles,
        "roles": formatted_roles
    }
    player = StaticPlayer.objects.select_related("team").filter(user=req.user, team__bracket__tournament_iteration=OCT4)
    if player:
        m = []
        for match in player[0].team.tournamentmatch_set.select_related("tournament_round").all():
            teams = match.teams.all()
            if match.team_order:
                teams = sorted(teams, key=lambda m: match.team_order.index(str(m.id)))
            match_info = {"obj": match}
            if not match.tournament_round.name == "QUALIFIERS":
                winner = None
                if match.wins:
                    team1_score = match.wins.count("1")
                    team2_score = match.wins.count("2")
                    winner = teams[0] if team1_score > team2_score else teams[1]
                match_info["team1"] = teams[0]
                match_info["team2"] = teams[1]
                match_info["score"] = f"{team1_score}-{team2_score}" if match.wins else "0-0"
                match_info["result"] = "UPCOMING" \
                    if match.starting_time is None or datetime.now(tz=timezone.utc) > match.starting_time \
                    else ("ONGOING" if winner is None else ("WON" if player.team == winner else "DEFEAT"))
            m.append(match_info)
        context["matches"] = m
   
    return render(req, "tournament/dashboard.html", context)


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

def matches(req, id=None):
    if id is None:
        return JsonResponse({"error": "Please give an id"})
    match = get_object_or_404(TournamentMatch, match_id=id)
    print(match)
    serializer = TournamentMatchSerializer(match)
    return JsonResponse(serializer.serialize(exclude=['tournament_round']), safe=False)


@cache_page(60)
def tournament_teams(req, name=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT4", section="teams")
    return render(req, "tournament/tournament_teams.html", {
        "tournament": tournament,
        "teams": map(
            lambda team: (team, sorted(team.get_players_with_user(), key=lambda p: p.osu_rank)),
            sorted(
                TournamentTeam.objects.filter(bracket__tournament_iteration=tournament),
                key=lambda t: ord(t.name.lower()[0])
            )
        ),
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
        if len(players) == 0:
            continue
        users.append({
            "role": role,
            "players": players,
            "count": len(players)
        })
    return render(req, "tournament/tournament_users.html", {
        "tournament": tournament,
        "users": users
    })


def referee(req):
    involvement = get_object_or_404(TournamentInvolvement, tournament_iteration=OCT4, user=req.user)
    if UserRoles.REFEREE not in involvement.roles:
        raise Http404()
    return render(req, "tournament/referee.html")
