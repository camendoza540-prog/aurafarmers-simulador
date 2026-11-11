from django.urls import path

from . import views

urlpatterns = [
    path("presets/", views.presets, name="scenario_presets"),
    path("simulate/", views.simulate, name="scenario_simulate"),
    path("history/", views.history, name="scenario_history"),
    path("history/<int:pk>/", views.delete_run, name="scenario_delete"),
]
