from django.urls import path
from django.views.decorators.cache import cache_page

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("teams", views.teams, name="teams"),
    path("bracket", views.bracket, name="bracket"),
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("tournaments", views.tournaments, name="tournaments"),
    path("tournaments/mappools", views.mappools, name="mappools"),
    path("tournaments/<str:name>", views.tournaments, name="named_tournament"),
    path("tournaments/<str:name>/mappool", views.mappools, name="named_mappools")
]
