from django.shortcuts import render
from django.templatetags.static import static
import os
import json




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