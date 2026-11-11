from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from market.testing import make_instruments
from portfolios.services import create_portfolio, execute_trade
from scenarios.presets import PRESETS_BY_KEY


class ScenarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_instruments(("SPY", "AAPL", "TLT", "GLD"))

    def setUp(self):
        self.user = get_user_model().objects.create_user("esc", "e@uis.edu.co", "Demo12345!")
        self.p = create_portfolio(self.user, "Test", Decimal("20000"))
        execute_trade(self.p, "SPY", "BUY", amount=Decimal("10000"))
        execute_trade(self.p, "TLT", "BUY", amount=Decimal("5000"))
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def _run(self, key, horizon=126):
        params = {**PRESETS_BY_KEY[key]["params"], "horizon_days": horizon}
        r = self.c.post("/api/scenarios/simulate/", {"portfolio_id": self.p.id, "preset": key, **params}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def test_crisis_is_worse_than_normal(self):
        normal = self._run("normal")
        crisis = self._run("crisis_2008")
        self.assertLess(crisis["summary"]["median_final"], normal["summary"]["median_final"])
        self.assertGreater(crisis["summary"]["prob_loss"], normal["summary"]["prob_loss"])

    def test_percentile_bands_are_ordered(self):
        data = self._run("covid_2020")
        for b in data["bands"]:
            self.assertLessEqual(b["p5"], b["p50"])
            self.assertLessEqual(b["p50"], b["p95"])

    def test_rate_hike_hurts_long_bonds(self):
        data = self._run("tasas_2022")
        tlt = next(a for a in data["assets"] if a["symbol"] == "TLT")
        self.assertLess(tlt["shock_pct"], -30)

    def test_empty_portfolio_is_rejected(self):
        empty = create_portfolio(self.user, "Vacío", Decimal("100"))
        r = self.c.post("/api/scenarios/simulate/", {"portfolio_id": empty.id}, format="json")
        self.assertEqual(r.status_code, 400)
