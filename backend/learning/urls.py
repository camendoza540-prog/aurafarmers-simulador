from django.urls import path

from . import views

urlpatterns = [
    path("lessons/", views.lessons, name="lessons"),
    path("lessons/<slug:slug>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<slug:slug>/quiz/", views.submit_quiz, name="lesson_quiz"),
    path("glossary/", views.glossary, name="glossary"),
]
