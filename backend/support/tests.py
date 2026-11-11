from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class SupportTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.user = U.objects.create_user("cliente", "c@uis.edu.co", "Demo12345!")
        self.agent = U.objects.create_user("agente", "s@uis.edu.co", "Demo12345!", is_staff=True)
        self.cu, self.cs = APIClient(), APIClient()
        self.cu.force_authenticate(self.user)
        self.cs.force_authenticate(self.agent)

    def test_ticket_lifecycle(self):
        r = self.cu.post("/api/support/tickets/", {"subject": "Duda CDT", "category": "ahorro", "body": "¿Por qué no puedo retirar mi CDT?"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["messages"]), 2)  # mensaje + respuesta automática
        tid = r.data["id"]
        other = get_user_model().objects.create_user("otro", "o@uis.edu.co", "Demo12345!")
        co = APIClient()
        co.force_authenticate(other)
        self.assertEqual(co.get(f"/api/support/tickets/{tid}/").status_code, 404)
        self.assertEqual(len(self.cs.get("/api/support/tickets/?status=open").data), 1)
        r = self.cs.post(f"/api/support/tickets/{tid}/messages/", {"body": "Debes esperar al vencimiento."}, format="json")
        self.assertEqual(r.data["status"], "answered")
        self.assertEqual(self.cu.get("/api/social/summary/").data["support_unread"], 1)
        self.cu.get(f"/api/support/tickets/{tid}/")
        self.assertEqual(self.cu.get("/api/social/summary/").data["support_unread"], 0)
