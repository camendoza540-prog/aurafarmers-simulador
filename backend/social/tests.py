from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class SocialTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.a = U.objects.create_user("andrea", "a@uis.edu.co", "Demo12345!", first_name="Andrea")
        self.b = U.objects.create_user("bruno", "b@uis.edu.co", "Demo12345!", first_name="Bruno")
        self.ca, self.cb = APIClient(), APIClient()
        self.ca.force_authenticate(self.a)
        self.cb.force_authenticate(self.b)

    def test_cannot_message_before_accepting(self):
        r = self.ca.post(f"/api/social/messages/{self.b.id}/", {"body": "hola"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_full_flow_search_request_accept_chat(self):
        found = self.ca.get("/api/social/users/?q=bru").data
        self.assertEqual(found[0]["relationship"]["status"], "none")
        self.assertEqual(self.ca.post("/api/social/requests/", {"to_user": self.b.id}, format="json").status_code, 201)
        incoming = self.cb.get("/api/social/requests/").data["incoming"]
        self.assertEqual(len(incoming), 1)
        self.cb.post(f"/api/social/requests/{incoming[0]['id']}/accept/")
        self.assertEqual(self.ca.post(f"/api/social/messages/{self.b.id}/", {"body": "¿Viste $AAPL?"}, format="json").status_code, 201)
        self.assertEqual(self.cb.get("/api/social/summary/").data["unread_messages"], 1)
        conv = self.cb.get(f"/api/social/messages/{self.a.id}/").data
        self.assertEqual(conv["messages"][0]["body"], "¿Viste $AAPL?")
        self.assertEqual(self.cb.get("/api/social/summary/").data["unread_messages"], 0)
