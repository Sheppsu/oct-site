from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model, login as _login, logout as _logout
from django.http import (
    HttpResponseBadRequest,
    HttpResponseServerError,
    Http404,
    JsonResponse,
    HttpResponseForbidden
)
from django.core.cache import cache
from django.db import connection

from .serializers import *
from common import render, get_auth_handler, log_err, parse_sql_row

import requests
import traceback
from osu.path import Path


User = get_user_model()
OCT5 = TournamentIteration.objects.get(name="OCT5")
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
        teams = []
        team_ids = []
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT (
                    tournament_tournamentteam.id,
                    tournament_tournamentteam.name,
                    tournament_tournamentteam.icon,
                    tournament_tournamentteam.seed,
                    tournament_staticplayer.osu_rank,
                    tournament_staticplayer.is_captain,
                    tournament_staticplayer.tier,
                    tournament_user.osu_username,
                    tournament_user.osu_avatar,
                    tournament_user.osu_id
                ) FROM tournament_tournamentteam
                INNER JOIN tournament_tournamentbracket ON (tournament_tournamentteam.bracket_id = tournament_tournamentbracket.id)
                INNER JOIN tournament_staticplayer ON (tournament_staticplayer.team_id = tournament_tournamentteam.id)
                INNER JOIN tournament_user ON (tournament_user.id = tournament_staticplayer.user_id)
                WHERE tournament_iteration_id = '%s'
                """ % tournament.name
            )
            bool_transform = lambda value: True if value == "t" else False
            rows = tuple(map(
                lambda row: parse_sql_row(row[0], [int, str, str, int, int, bool_transform, str, str, str, int]),
                cursor.fetchall()
            ))
            for row in rows:
                if row[0] not in team_ids:
                    team_ids.append(row[0])
                    teams.append({"name": row[1], "icon": row[2], "seed": row[3], "players": []})
                teams[team_ids.index(row[0])]["players"].append({"osu_rank": row[4], "is_captain": row[5], "tier": row[6], "osu_username": row[7], "osu_avatar": row[8], "osu_id": row[9]})
        for team in teams:
            team["players"] = sorted(team["players"], key=lambda player: 0 if player["is_captain"] else player["osu_rank"])
        teams = sorted(teams, key=lambda team: team["players"][0]["osu_rank"])
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
            .select_related("tournament_round", "referee", "streamer", "commentator1", "commentator2")
            .prefetch_related("teams__players__user")
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
        log_err(req, exc)
        return HttpResponseBadRequest()
    except Exception as exc:
        log_err(req, exc)
    return HttpResponseServerError()


def logout(req):
    if req.user.is_authenticated:
        _logout(req)
    return redirect("index")


def dashboard(req):
    if not req.user.is_authenticated:
        return redirect("index")
    involvement = req.user.get_tournament_involvement(tournament_iteration=OCT5)
    roles = sorted(involvement[0].roles.get_roles(), key=lambda r: USER_DISPLAY_ORDER.index(r)) \
        if involvement else None
    formatted_roles = ", ".join(map(lambda r: r.name[0]+r.name[1:].replace("_", " ").lower(), roles)) \
        if roles else "No Roles"

    context = {
        "is_registered": involvement and UserRoles.REGISTERED_PLAYER in involvement[0].roles,
        "roles": formatted_roles
    }
    player = StaticPlayer.objects.select_related("team").filter(
        user=req.user,
        team__bracket__tournament_iteration=OCT5
    ).first()
    if player is not None:
        context["matches"] = filter(lambda m: m is not None, map(
            lambda m: map_match_object(m, player),
            sorted(player.team.tournamentmatch_set.prefetch_related("teams").select_related("tournament_round__bracket").all(), reverse=True)
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
        return redirect("tournament_section", name="OCT5", section="mappool")

    if kwargs.get("api"):
        round = TournamentRound.objects\
            .select_related("mappool", "mappool")\
            .get(bracket__tournament_iteration=tournament, name=round.upper())
        if not round:
            raise Http404()
        maps = sorted(round.mappool.mappoolbeatmap_set.all(), key=lambda m: m.id)
        serializer = MappoolBeatmapSerializer(maps, many=True)
        return JsonResponse(serializer.serialize(), safe=False)

    return render(req, "tournament/tournament_mappool.html", {
        "mappools": get_mappools(tournament),
        "tournament": tournament,
    })


def tournament_teams(req, name=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT5", section="teams")
    return render(req, "tournament/tournament_teams.html", {
        "tournament": tournament,
        "teams": get_teams(tournament),
    })


def tournament_bracket(req, name=None, **kwargs):
    tournament = get_tournament(name, kwargs)
    if tournament is None:
        return redirect("tournament_section", name="OCT5", section="bracket")
    return render(req, "tournament/tournament_bracket.html", {
        "tournament": tournament,
        "bracket": tournament.get_brackets()[0]
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


def map_match_object(match, player=None):
    match_info = {"obj": match}
    progress = match.get_progress()
    match_info["progress"] = progress
    if match.tournament_round.name != "QUALIFIERS":
        teams = match.teams.all()
        if match.team_order and teams:
            teams = sorted(teams, key=lambda m: match.team_order.index(str(m.id)))
        winner = None
        if match.wins:
            team1_score = match.wins.count("1")
            team2_score = match.wins.count("2")
            match_info["score"] = f"{team1_score}-{team2_score}"
            winner = teams[0] if team1_score > team2_score else teams[1]
        match_info["team1"] = teams[0] if len(teams) > 0 else None
        match_info["team2"] = teams[1] if len(teams) > 1 else None
        if player is not None:
            match_info["result"] = progress if progress != "FINISHED" else ("WON" if player.team == winner else "DEFEAT")
        else:
            match_info["result"] = progress
        match_info["id"] = f"M{match.match_id}"
    else:
        match_info["result"] = "QUALIFIERS"
        match_info["team_names"] = ", ".join(map(lambda team: team.name, match.teams.all()))
        match_info["id"] = f"Q{match.match_id}"
    match_info["color"] = {
        "FINISHED": "#8AFF8A",
        "UPCOMING": "#AAAAAA",
        "ONGOING": "#8A8AFF",
        "WON": "#8AFF8A",
        "DEFEAT": "#FF8A8A",
        "QUALIFIERS": "#AAAAAA" if not match.finished else "#8A8AFF",
    }[match_info["result"]]
    return match_info


def parse_match_id(match_id):
    match_id = match_id.upper()
    if len(match_id) < 2:
        raise Http404()
    is_quals = match_id[0] == "Q"
    if match_id[0] != "M" and not is_quals:
        raise Http404()
    try:
        return int(match_id[1:]), is_quals
    except ValueError:
        raise Http404()


def get_matches_from_id(tournament, match_id=None):
    if match_id is None:
        return get_matches(tournament)
    match_id, is_quals = parse_match_id(match_id)
    try:
        return TournamentMatch.objects\
            .exclude(tournament_round__name="QUALIFIERS")\
            .prefetch_related("teams")\
            .select_related("tournament_round__bracket", "referee", "streamer", "commentator1", "commentator2")\
            .get(match_id=match_id, tournament_round__bracket__tournament_iteration=tournament) \
            if not is_quals else \
            TournamentMatch.objects \
            .prefetch_related("teams") \
            .select_related("tournament_round__bracket", "referee", "streamer", "commentator1", "commentator2")\
            .get(match_id=match_id, tournament_round__name="QUALIFIERS", tournament_round__bracket__tournament_iteration=tournament)
    except TournamentMatch.DoesNotExist:
        raise Http404()


def get_user_as_player(bracket, user):
    return StaticPlayer.objects.select_related("team")\
        .filter(user=user, team__bracket=bracket)\
        .first()


def render_match(req, tournament, match):
    match_info = map_match_object(match)
    in_lobby = False
    current_player = None
    involvement = None
    if req.user.is_authenticated and match_info["result"] == "QUALIFIERS":
        current_player = get_user_as_player(match.tournament_round.bracket_id, req.user)
        involvement = TournamentInvolvement.objects\
            .filter(user=req.user, tournament_iteration=match.tournament_round.bracket.tournament_iteration_id)\
            .first()
        if current_player is not None:
            in_lobby = any(map(lambda team: team.id == current_player.team.id, match.teams.all()))
    allowed_actions = (
        current_player is not None and current_player.is_captain and match_info["progress"] == "UPCOMING",
        UserRoles.REFEREE in involvement.roles
    ) if req.user.is_authenticated else ()
    return render(req, "tournament/tournament_match.html", {
        "tournament": tournament,
        "match": match_info,
        "allowed_actions": allowed_actions,
        "show_actions": any(allowed_actions),
        "in_lobby": in_lobby
    })


def tournament_matches(req, name, match_id=None, **kwargs):
    # TODO: match pages need some functions to optimize the queries
    tournament = kwargs.get("tournament") or get_object_or_404(TournamentIteration, name=name.upper())
    matches = get_matches_from_id(tournament, match_id)

    if kwargs.get("api"):
        serializer = TournamentMatchSerializer(matches, many=match_id is None)
        return JsonResponse(serializer.serialize(exclude=["tournament_round.bracket"]), safe=False)

    if match_id is None:
        matches_full = tuple(filter(lambda m: m is not None, map(map_match_object, matches)))
        if req.user.is_authenticated:
            involvement = TournamentInvolvement.objects.filter(user=req.user, tournament_iteration=tournament).first()
            if involvement is not None and UserRoles.REFEREE in involvement.roles:
                for info in matches_full:
                    info["can_staff"] = info["obj"].referee_id is None

        return render(req, "tournament/tournament_matches.html", {
            "tournament": tournament,
            "matches": matches_full,
        })
    return render_match(req, tournament, matches)


def action_handler(valid_actions, select_related):
    def wrapper(func):
        def inner_wrapper(req, match_id, action):
            if action not in valid_actions:
                raise Http404()

            return_page = redirect(req.GET.get("state", "/"))

            if not req.user.is_authenticated:
                return return_page

            match = TournamentMatch.objects.select_related(*select_related).filter(id=match_id).first()

            return func(req, match_id, action, return_page, match)
        return inner_wrapper
    return wrapper


@action_handler(("join", "leave"), ("tournament_round__bracket", "referee"))
def handle_ref_action(req, match_id, action, return_page, match):
    if match.referee is not None and match.referee.id != req.user.id:
        return return_page
    if match.referee is not None and action != "leave":
        return return_page

    involvement = TournamentInvolvement.objects.filter(
        user=req.user,
        tournament_iteration=match.tournament_round.bracket.tournament_iteration_id
    ).first()
    if involvement is None or UserRoles.REFEREE not in involvement.roles:
        return return_page

    if action == "join":
        match.referee = req.user
        match.save()
    else:
        match.referee = None
        match.save()
    return return_page


@action_handler(("join", "leave"), ("tournament_round",))
def handle_player_action(req, match_id, action, return_page, match):
    if match.get_progress() != "UPCOMING":
        return return_page
    if match.tournament_round.name != "QUALIFIERS":
        return return_page

    player = get_user_as_player(match.tournament_round.bracket_id, req.user)
    if player is None:
        return return_page
    if not player.is_captain:
        return return_page
    if action == "leave":
        match.remove_team(player.team)
        return return_page
    other_match = TournamentMatch.objects.filter(teams=player.team, tournament_round=match.tournament_round)
    if other_match:
        other_match = other_match[0]
        if other_match.get_progress() != "UPCOMING":
            return return_page
        other_match.remove_team(player.team)
    match.add_team(player.team)
    return return_page


def tournament_match_action(req, match_id, action):
    action_handlers = {
        "player": handle_player_action,
        "ref": handle_ref_action
    }

    action = action.lower()
    for prefix, handler in action_handlers.items():
        if action.startswith(prefix+"_"):
            return handler(req, match_id, action[len(prefix)+1:])

    raise Http404()


def referee(req):
    if not req.user.is_authenticated:
        return HttpResponseForbidden()
    involvement = get_object_or_404(TournamentInvolvement, tournament_iteration=OCT5, user=req.user)
    if UserRoles.REFEREE not in involvement.roles:
        return HttpResponseForbidden()
    return render(req, "tournament/refereev1.html")


def get_osu_match_info(req):
    if not req.user.is_authenticated:
        return HttpResponseForbidden()
    involvement = get_object_or_404(TournamentInvolvement, tournament_iteration=OCT5, user=req.user)
    if UserRoles.REFEREE not in involvement.roles:
        return HttpResponseForbidden()

    try:
        match_id = int(req.GET.get("match_id", None))
    except ValueError:
        return HttpResponseBadRequest()

    client = Client(req.user.get_auth_handler())
    return JsonResponse(client.http.make_request(Path.get_match(match_id)), safe=False)


def register(req):
    if not req.user.is_authenticated:
        return redirect("index")
    involvement = req.user.get_tournament_involvement(tournament_iteration=OCT5)
    if not involvement:
        TournamentInvolvement.objects.create(
            user=req.user,
            tournament_iteration=OCT5,
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
    involvement = req.user.get_tournament_involvement(tournament_iteration=OCT5)
    if not involvement or UserRoles.REGISTERED_PLAYER not in involvement[0].roles:
        return redirect("index")
    involvement = involvement[0]
    involvement.roles = UserRoles(involvement.roles - UserRoles.REGISTERED_PLAYER)
    involvement.save()
    return redirect("dashboard")
