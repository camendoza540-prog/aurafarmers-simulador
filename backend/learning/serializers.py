from rest_framework import serializers

from .models import GlossaryTerm, Lesson, QuizQuestion


class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = ["id", "question", "options"]


class LessonListSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    completed = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["slug", "title", "category", "category_label", "level", "level_label", "summary",
                  "minutes", "order", "completed", "score"]

    def _progress(self, obj):
        return self.context.get("progress", {}).get(obj.id)

    def get_completed(self, obj):
        return self._progress(obj) is not None

    def get_score(self, obj):
        p = self._progress(obj)
        return {"score": p.score, "total": p.total} if p else None


class LessonDetailSerializer(LessonListSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)

    class Meta(LessonListSerializer.Meta):
        fields = LessonListSerializer.Meta.fields + ["content", "try_it", "questions"]


class GlossaryTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlossaryTerm
        fields = ["id", "term", "definition"]
