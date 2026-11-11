from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import InsufficientFunds


class AuthTests(TestCase):
    def setUp(self):
        self.c = APIClient()

    def test_register_creates_profile_with_initial_balance_and_tokens(self):
        r = self.c.post("/api/auth/register/", {
            "username": "camilo", "email": "camilo@uis.edu.co", "first_name": "Camilo",
            "password": "Inversion2026!", "password2": "Inversion2026!", "risk_profile": "agresivo",
            "accept_terms": True,
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIn("access", r.data["tokens"])
        user = get_user_model().objects.get(username="camilo")
        self.assertEqual(user.profile.cash_balance, settings.SIMULATION["INITIAL_BALANCE"])
        self.assertEqual(user.profile.risk_profile, "agresivo")
        # Ley 1581: queda registrada la fecha y la versión aceptada
        self.assertIsNotNone(user.profile.terms_accepted_at)
        self.assertEqual(user.profile.terms_version, settings.LEGAL["TERMS_VERSION"])
        self.assertTrue(r.data["user"]["profile"]["terms_current"])

    def test_register_requires_accepting_terms(self):
        for value in (None, False):
            data = {"username": "sinterminos", "email": "s@uis.edu.co", "first_name": "S",
                    "password": "Inversion2026!", "password2": "Inversion2026!"}
            if value is not None:
                data["accept_terms"] = value
            r = self.c.post("/api/auth/register/", data, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertIn("accept_terms", r.data)
        self.assertFalse(get_user_model().objects.filter(username="sinterminos").exists())

    def test_register_rejects_mismatched_passwords(self):
        r = self.c.post("/api/auth/register/", {
            "username": "xavier", "email": "x@uis.edu.co", "first_name": "X",
            "password": "Inversion2026!", "password2": "Otra2026!!", "accept_terms": True,
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("password2", r.data)

    def test_login_returns_jwt(self):
        get_user_model().objects.create_user("demo2", "d@uis.edu.co", "Demo12345!")
        r = self.c.post("/api/auth/login/", {"username": "demo2", "password": "Demo12345!"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_debit_is_atomic_and_rejects_overdraft(self):
        user = get_user_model().objects.create_user("p", "p@uis.edu.co", "Demo12345!")
        stale = get_user_model().objects.get(pk=user.pk).profile  # instancia "vieja"
        user.profile.debit(Decimal("60000"))
        stale.debit(Decimal("30000"))  # no debe sobrescribir el débito anterior
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.cash_balance, Decimal("10000.00"))
        with self.assertRaises(InsufficientFunds):
            user.profile.debit(Decimal("10000.01"))


class ThrottleTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_login_is_rate_limited(self):
        c = APIClient()
        codes = [c.post("/api/auth/login/", {"username": "nadie", "password": "x"}, format="json").status_code for _ in range(12)]
        self.assertIn(429, codes)
        from django.core.cache import cache
        cache.clear()


class ProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("perfil", "p@uis.edu.co", "Demo12345!")
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_change_password_requires_matching_confirmation(self):
        r = self.c.post("/api/auth/change-password/", {"current_password": "Demo12345!", "new_password": "Otra2026!xy", "new_password2": "Distinta2026!"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/auth/change-password/", {"current_password": "Demo12345!", "new_password": "Otra2026!xy", "new_password2": "Otra2026!xy"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data["tokens"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Otra2026!xy"))

    def test_avatar_upload_is_cropped(self):
        import tempfile
        from io import BytesIO

        from django.test import override_settings
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (900, 500), (200, 100, 30)).save(buf, "PNG")
        buf.seek(0)
        buf.name = "foto.png"
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            r = self.c.post("/api/auth/avatar/", {"avatar": buf}, format="multipart")
            self.assertEqual(r.status_code, 200)
            self.user.profile.refresh_from_db()
            self.assertEqual(Image.open(self.user.profile.avatar.path).size, (320, 320))

    def test_rejects_non_image(self):
        from io import BytesIO
        f = BytesIO(b"no soy una imagen")
        f.name = "x.png"
        self.assertEqual(self.c.post("/api/auth/avatar/", {"avatar": f}, format="multipart").status_code, 400)


class SimulationServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from market.testing import make_instruments
        make_instruments(("SPY", "KO"))

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        U = get_user_model()
        self.a = U.objects.create_user("gana", "g@uis.edu.co", "Demo12345!", first_name="Gana")
        self.b = U.objects.create_user("pierde", "p2@uis.edu.co", "Demo12345!", first_name="Pierde")

    def test_net_worth_adds_cash_portfolios_and_savings(self):
        from portfolios.services import create_portfolio
        from savings.services import open_account
        from users.services import net_worth
        create_portfolio(self.a, "P", Decimal("20000"))
        open_account(self.a, "AHORRO", Decimal("5000"))
        nw = net_worth(self.a)
        self.assertEqual(nw["cash"], Decimal("75000.00"))
        self.assertAlmostEqual(float(nw["total"]), 100000, delta=1)

    def test_ranking_orders_by_profit_and_respects_privacy(self):
        from django.core.cache import cache
        from users.services import ranking
        self.b.profile.debit(Decimal("1000"))  # simula una pérdida
        rows = ranking(10)
        self.assertEqual(rows[0]["username"], "gana")
        self.b.profile.show_in_ranking = False
        self.b.profile.save()
        cache.delete_many(["ranking:all", "ranking:stale"])
        self.assertNotIn("pierde", [r["username"] for r in ranking(10)])
        self.assertIn("pierde", [r["username"] for r in ranking(10, me=self.b)])

    def test_reset_restores_balance_and_removes_activity(self):
        from portfolios.services import create_portfolio
        from users.services import reset_simulation
        create_portfolio(self.a, "P", Decimal("30000"))
        reset_simulation(self.a)
        self.a.profile.refresh_from_db()
        self.assertEqual(self.a.profile.cash_balance, Decimal("100000.00"))
        self.assertFalse(self.a.portfolios.exists())



class PrivacyTests(TestCase):
    """Ley 1581: aceptación de la versión vigente y derecho de supresión."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        U = get_user_model()
        self.user = U.objects.create_user("antiguo", "a@uis.edu.co", "Demo12345!")
        self.other = U.objects.create_user("amiga", "b@uis.edu.co", "Demo12345!")
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_legacy_account_must_accept_current_terms(self):
        r = self.c.get("/api/auth/me/")
        self.assertFalse(r.data["profile"]["terms_current"])
        self.assertEqual(self.c.post("/api/auth/accept-terms/", {}, format="json").status_code, 400)
        r = self.c.post("/api/auth/accept-terms/", {"accept": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["profile"]["terms_current"])

    def test_delete_account_requires_password_and_confirmation(self):
        url = "/api/auth/delete-account/"
        self.assertEqual(self.c.post(url, {"password": "mala", "confirm": "ELIMINAR"}, format="json").status_code, 400)
        self.assertEqual(self.c.post(url, {"password": "Demo12345!", "confirm": "si"}, format="json").status_code, 400)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_delete_account_removes_all_personal_data(self):
        from portfolios.services import create_portfolio
        from social.models import FriendRequest, Message
        create_portfolio(self.user, "Mío", Decimal("1000"))
        FriendRequest.objects.create(from_user=self.user, to_user=self.other, status="accepted")
        Message.objects.create(sender=self.user, recipient=self.other, body="hola")
        r = self.c.post("/api/support/tickets/", {"category": "cuenta", "subject": "Mi cuenta",
                                                  "body": "Quiero saber cómo eliminar mi cuenta."}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.c.post("/api/auth/delete-account/", {"password": "Demo12345!", "confirm": "ELIMINAR"}, format="json")
        self.assertEqual(r.status_code, 204)
        pk = self.user.pk
        self.assertFalse(get_user_model().objects.filter(pk=pk).exists())
        from portfolios.models import Portfolio
        from support.models import SupportTicket
        self.assertFalse(Portfolio.objects.filter(user_id=pk).exists())
        self.assertFalse(Message.objects.filter(sender_id=pk).exists())
        self.assertFalse(FriendRequest.objects.filter(from_user_id=pk).exists())
        self.assertFalse(SupportTicket.objects.filter(user_id=pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())
