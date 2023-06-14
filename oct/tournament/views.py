from django.shortcuts import render


def index(req):
    return render(req, "tournament/index.html")


def teams(req):
    return render(req, "tournament/teams.html")

def mappools(req):
    return render(req, "tournament/mappools.html")

def bracket(req):
    return render(req, "tournament/bracket.html")