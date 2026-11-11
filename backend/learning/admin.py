from django.contrib import admin

from .models import GlossaryTerm, Lesson, LessonProgress, QuizQuestion


class QuizInline(admin.StackedInline):
    model = QuizQuestion
    extra = 0


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "category", "level", "minutes")
    list_display_links = ("title",)
    list_filter = ("category", "level")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [QuizInline]


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "score", "total", "completed_at")


@admin.register(GlossaryTerm)
class GlossaryAdmin(admin.ModelAdmin):
    list_display = ("term",)
    search_fields = ("term", "definition")
