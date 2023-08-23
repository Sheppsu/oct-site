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
        rounds = sorted(TournamentRound.objects.select_related("mappool").filter(bracket=bracket))
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


def get_teams(tournament: TournamentIteration):
    teams = cache.get(f"{tournament.name}_teams")
    if teams is None:
        teams = tuple(map(
            lambda team: (team, sorted(team.get_players_with_user(), key=lambda p: p.osu_rank)),
            sorted(
                TournamentTeam.objects.filter(bracket__tournament_iteration=tournament),
                key=lambda t: ord(t.name.lower()[0])
            )
        ))
        cache.set(f"{tournament.name}_teams", teams, 60)
    return teams


def get_users(tournament: TournamentIteration, involvements):
    users = cache.get(f"{tournament.name}_users")
    if users is None:
        users = []
        for enum in USER_DISPLAY_ORDER:
            role = " ".join(map(lambda string: string[0] + string[1:].lower(), enum.name.split("_"))) + "s"
            players = sorted(filter(lambda i: enum in i.roles, involvements), key=lambda i: i.join_date)
            if len(players) == 0:
                continue
            users.append({
                "role": role,
                "players": players,
                "count": len(players)
            })
        cache.set(f"{tournament.name}_users", users, 60)
    return users


def get_matches(tournament: TournamentIteration):
    matches = cache.get(f"{tournament.name}_matches")
    if matches is None:
        matches = sorted(
            TournamentMatch.objects
            .select_related("tournament_round")
            .filter(tournament_round__bracket__tournament_iteration=tournament),
            reverse=True)
        cache.set(f"{tournament.name}_matches", matches, 60)
    return matches


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


def _map_match_object(match, player=None):
    match_info = {"obj": match}
    result = match.get_progress()
    if match.tournament_round.name != "QUALIFIERS":
        teams = match.teams.all()
        if match.team_order and teams:
            teams = sorted(teams, key=lambda m: match.team_order.index(str(m.id)))
        winner = None
        if match.wins:
            team1_score = match.wins.count("1")
            team2_score = match.wins.count("2")
            winner = teams[0] if team1_score > team2_score else teams[1]
        match_info["team1"] = teams[0] if len(teams) > 0 else None
        match_info["team2"] = teams[1] if len(teams) > 1 else None
        match_info["score"] = f"{team1_score}-{team2_score}" if match.wins else "0-0"
        if player is not None:
            match_info["result"] = result if result != "FINISHED" else ("WON" if player.team == winner else "DEFEAT")
        else:
            match_info["result"] = result
    else:
        match_info["result"] = "QUALIFIERS"
    match_info["color"] = {
        "FINISHED": "#8AFF8A",
        "UPCOMING": "#AAAAAA",
        "ONGOING": "#8A8AFF",
        "WON": "#8AFF8A",
        "DEFEAT": "#FF8A8A",
        "QUALIFIERS": "#AAAAAA" if not match.finished else "#8A8AFF",
    }[match_info["result"]]
    return match_info


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
        player = player[0]
        context["matches"] = filter(lambda m: m is not None, map(
            lambda m: _map_match_object(m, player),
            sorted(player.team.tournamentmatch_set.select_related("tournament_round").all(), reverse=True)
        ))
   
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
            "users": tournament_users,
            "matches": tournament_matches,
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


def tournament_mappools(req, name=None, round=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT4", section="mappool")

    if kwargs.get("api"):
        round = TournamentRound.objects\
            .select_related("mappool", "mappool")\
            .get(bracket__tournament_iteration=tournament, name=round.upper())
        if not round:
            raise Http404()
        maps = round.mappool.mappoolbeatmap_set.all()
        serializer = MappoolBeatmapSerializer(maps, many=True)
        return JsonResponse(serializer.serialize(), safe=False)

    return render(req, "tournament/tournament_mappool.html", {
        "mappools": get_mappools(tournament),
        "tournament": tournament,
    })


def tournament_teams(req, name=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT4", section="teams")
    return render(req, "tournament/tournament_teams.html", {
        "tournament": tournament,
        "teams": get_teams(tournament),
    })


def tournament_bracket(req, name=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT4", section="bracket")
    return render(req, "tournament/tournament_bracket.html", {
        "tournament": tournament
    })


def tournament_users(req, name, **kwargs):
    tournament = kwargs.get("tournament") or get_object_or_404(TournamentIteration, name=name.upper())
    involvements = TournamentInvolvement.objects \
        .select_related("user") \
        .filter(tournament_iteration=tournament)

    if kwargs.get("api"):
        serializer = TournamentInvolvementSerializer(involvements, many=True)
        return JsonResponse(serializer.serialize(exclude=["tournament_iteration"]), safe=False)

    return render(req, "tournament/tournament_users.html", {
        "tournament": tournament,
        "users": get_users(tournament, involvements)
    })


def tournament_matches(req, name, match_id=None, **kwargs):
    tournament = kwargs.get("tournament") or get_object_or_404(TournamentIteration, name=name.upper())
    if match_id is None:
        matches = get_matches(tournament)
    else:
        quals = req.GET.get("quals", "").lower() == "true"
        matches = TournamentMatch.objects.exclude(tournament_round__name="QUALIFIERS").get(match_id=match_id) \
            if not quals else TournamentMatch.objects.get(match_id=match_id, tournament_round__name="QUALIFIERS")

    if kwargs.get("api"):
        serializer = TournamentMatchSerializer(matches, many=match_id is None)
        return JsonResponse(serializer.serialize(exclude=["tournament_round.bracket"]), safe=False)

    return render(req, "tournament/tournament_matches.html", {
        "tournament": tournament,
        "matches": filter(lambda m: m is not None, map(_map_match_object, matches)),
    })


def referee(req):
    involvement = get_object_or_404(TournamentInvolvement, tournament_iteration=OCT4, user=req.user)
    if UserRoles.REFEREE not in involvement.roles:
        raise Http404()
    return render(req, "tournament/referee.html")
