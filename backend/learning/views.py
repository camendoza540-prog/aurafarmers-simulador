from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import GlossaryTerm, Lesson, LessonProgress
from .serializers import GlossaryTermSerializer, LessonDetailSerializer, LessonListSerializer


def _progress_map(user):
    return {p.lesson_id: p for p in LessonProgress.objects.filter(user=user)}


@api_view(["GET"])
def lessons(request):
    ctx = {"progress": _progress_map(request.user)}
    qs = Lesson.objects.all()
    data = LessonListSerializer(qs, many=True, context=ctx).data
    return Response({"lessons": data, "completed": len(ctx["progress"]), "total": qs.count()})


@api_view(["GET"])
def lesson_detail(request, slug):
    lesson = get_object_or_404(Lesson.objects.prefetch_related("questions"), slug=slug)
    data = LessonDetailSerializer(lesson, context={"progress": _progress_map(request.user)}).data
    ordered = list(Lesson.objects.values_list("slug", "title"))
    idx = [s for s, _ in ordered].index(slug)
    data["previous"] = dict(zip(("slug", "title"), ordered[idx - 1])) if idx > 0 else None
    data["next"] = dict(zip(("slug", "title"), ordered[idx + 1])) if idx < len(ordered) - 1 else None
    return Response(data)


@api_view(["POST"])
def submit_quiz(request, slug):
    """Recibe {"answers": {question_id: option_index}} y devuelve la corrección."""
    lesson = get_object_or_404(Lesson, slug=slug)
    answers = request.data.get("answers", {}) or {}
    results, score = [], 0
    for q in lesson.questions.all():
        chosen = answers.get(str(q.id), answers.get(q.id))
        correct = chosen is not None and int(chosen) == q.correct_index
        score += int(correct)
        results.append({"id": q.id, "chosen": chosen, "correct_index": q.correct_index,
                        "correct": correct, "explanation": q.explanation})
    total = len(results)
    LessonProgress.objects.update_or_create(user=request.user, lesson=lesson, defaults={"score": score, "total": total})
    return Response({"score": score, "total": total, "results": results})


@api_view(["GET"])
def glossary(request):
    return Response(GlossaryTermSerializer(GlossaryTerm.objects.all(), many=True).data)
