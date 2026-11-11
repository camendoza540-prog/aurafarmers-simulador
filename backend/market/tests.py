from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from market.models import Instrument
from market.services.engine import tick
from market.testing import make_instruments


class MarketEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.insts = make_instruments(("SPY", "AAPL"))

    def test_history_ends_at_anchor_price(self):
        spy = self.insts["SPY"]
        last = spy.bars.order_by("-date").first()
        self.assertEqual(last.close, spy.anchor_price)
        self.assertGreater(spy.bars.count(), 240)

    def test_bars_are_consistent(self):
        for bar in self.insts["AAPL"].bars.all()[:200]:
            self.assertLessEqual(bar.low, min(bar.open, bar.close))
            self.assertGreaterEqual(bar.high, max(bar.open, bar.close))

    def test_tick_moves_price_after_elapsed_time(self):
        from django.core.cache import cache
        cache.clear()
        spy = self.insts["SPY"]
        before = spy.current_price
        spy.last_tick_at = timezone.now() - timedelta(minutes=10)
        spy.save()
        self.assertTrue(tick(spy))
        spy.refresh_from_db()
        self.assertNotEqual(before, spy.current_price)

    def test_api_requires_authentication(self):
        self.assertEqual(APIClient().get("/api/market/instruments/").status_code, 401)

    def test_instrument_detail_has_stats(self):
        user = get_user_model().objects.create_user("ana", "ana@uis.edu.co", "ClaveSegura2026")
        c = APIClient()
        c.force_authenticate(user)
        r = c.get("/api/market/instruments/AAPL/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("volatility_annual", r.data["stats"])
        r = c.get("/api/market/instruments/AAPL/history/?range=3M")
        self.assertGreater(len(r.data["bars"]), 50)


class MarketClockAndCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.insts = make_instruments(("SPY", "AAPL"))

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_clock_is_disabled_during_tests_and_refresh_falls_back(self):
        from django.utils import timezone
        from datetime import timedelta
        from market.services.engine import clock_running, refresh_all, start_market_clock
        self.assertFalse(start_market_clock())
        self.assertFalse(clock_running())
        Instrument.objects.update(last_tick_at=timezone.now() - timedelta(minutes=5))
        refresh_all()  # sin reloj, la petición actualiza los precios por sí misma
        self.assertTrue(all((timezone.now() - i.last_tick_at).total_seconds() < 60 for i in Instrument.objects.all()))
        refresh_all()  # el candado evita una segunda actualización inmediata

    def test_tick_lock_prevents_duplicate_writes(self):
        from django.utils import timezone
        from datetime import timedelta
        from market.services.engine import tick
        spy = self.insts["SPY"]
        spy.last_tick_at = timezone.now() - timedelta(minutes=2)
        spy.save(update_fields=["last_tick_at"])
        self.assertTrue(tick(spy))
        spy.last_tick_at = timezone.now() - timedelta(minutes=2)
        self.assertFalse(tick(spy))  # otra petición en el mismo segundo no vuelve a escribir

    def test_sparkline_is_cached_and_ends_at_live_price(self):
        from decimal import Decimal
        from market.services.stats import sparkline
        spy = Instrument.objects.get(symbol="SPY")
        first = sparkline(spy)
        self.assertEqual(len(first), 30)
        spy.current_price = Decimal("123.4500")
        self.assertEqual(sparkline(spy)[-1], 123.45)
        self.assertEqual(sparkline(spy)[:-1], first[:-1])
