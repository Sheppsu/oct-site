from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("teams", views.teams, name="teams"),
    path("mappools", views.mappools, name="mappools"),
    path("bracket", views.bracket, name="bracket"),
    path("login", views.login, name="login"),
    path("dashboard", views.dashboard, name="dashboard")
]
