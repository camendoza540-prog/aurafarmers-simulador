from django.conf import settings
from django.db import models


class Lesson(models.Model):
    CATEGORY_CHOICES = [
        ("fundamentos", "Fundamentos"),
        ("instrumentos", "Instrumentos"),
        ("riesgo", "Riesgo y rendimiento"),
        ("estrategia", "Estrategia"),
    ]
    LEVEL_CHOICES = [("basico", "Básico"), ("intermedio", "Intermedio")]

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    level = models.CharField(max_length=12, choices=LEVEL_CHOICES, default="basico")
    summary = models.CharField(max_length=240)
    content = models.TextField(help_text="Markdown")
    minutes = models.PositiveSmallIntegerField(default=5)
    order = models.PositiveSmallIntegerField(default=0)
    try_it = models.CharField("Ruta para practicar", max_length=60, blank=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Lección"
        verbose_name_plural = "Lecciones"

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="questions")
    question = models.CharField(max_length=240)
    options = models.JSONField()
    correct_index = models.PositiveSmallIntegerField()
    explanation = models.CharField(max_length=300)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    score = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "lesson")
        verbose_name = "Progreso"
        verbose_name_plural = "Progreso de lecciones"


class GlossaryTerm(models.Model):
    term = models.CharField(max_length=60, unique=True)
    definition = models.TextField()

    class Meta:
        ordering = ["term"]
        verbose_name = "Término"
        verbose_name_plural = "Glosario"

    def __str__(self):
        return self.term
