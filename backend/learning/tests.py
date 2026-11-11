from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from learning.seed_data import seed_learning


class LearningTests(TestCase):
    def setUp(self):
        seed_learning()
        self.user = get_user_model().objects.create_user("est", "e@uis.edu.co", "Demo12345!")
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_quiz_scoring_and_progress(self):
        lesson = self.c.get("/api/learning/lessons/etfs/").data
        self.assertNotIn("correct_index", lesson["questions"][0])  # no se filtran las respuestas
        answers = {str(q["id"]): 0 for q in lesson["questions"]}
        r = self.c.post("/api/learning/lessons/etfs/quiz/", {"answers": answers}, format="json")
        self.assertEqual(r.data["total"], 3)
        listing = self.c.get("/api/learning/lessons/").data
        self.assertEqual(listing["completed"], 1)
