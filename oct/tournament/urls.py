from django.urls import path

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
    path("tournaments/<str:name>", views.tournaments, name="tournament_info"),
    path("tournaments/<str:name>/<str:section>", views.tournaments, name="tournament_section"),
    path("register", views.register, name="register"),
    path("unregister", views.unregister, name="unregister"),
    path("referee", views.referee, name="referee")
]
