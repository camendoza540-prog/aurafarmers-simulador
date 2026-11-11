from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from market.testing import make_instruments
from portfolios.models import Position
from portfolios.services import create_portfolio, execute_trade, valuate_portfolio
from portfolios.trading import TradingError, check_triggers, close_position, margin_status, open_position


class MarginTradingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.insts = make_instruments(("SPY", "AAPL", "GLD", "XAUUSD", "EURUSD", "USDJPY", "USDCOP", "BTCUSD"))

    def setUp(self):
        self.user = get_user_model().objects.create_user("trader", "t@uis.edu.co", "Demo12345!")
        self.p = create_portfolio(self.user, "Margen", Decimal("10000"))

    def _move(self, symbol, factor):
        inst = self.insts[symbol]
        inst.refresh_from_db()
        inst.current_price = (inst.current_price * Decimal(str(factor))).quantize(Decimal("0.0001"))
        inst.last_tick_at = timezone.now()
        inst.save()
        return inst

    def test_open_long_blocks_margin_and_uses_ask(self):
        pos = open_position(self.p, "SPY", "LONG", leverage=5, margin_amount=Decimal("1000"))
        self.p.refresh_from_db()
        self.assertEqual(pos.margin, Decimal("1000.00"))
        self.assertEqual(self.p.cash, Decimal("9000.00"))
        self.assertEqual(pos.entry_price, pos.instrument.ask)
        self.assertAlmostEqual(float(pos.notional), 5000, delta=1)

    def test_leverage_limited_by_asset_class(self):
        with self.assertRaises(TradingError):
            open_position(self.p, "AAPL", "LONG", leverage=10, margin_amount=Decimal("100"))
        with self.assertRaises(TradingError):  # un ETF de oro sigue siendo ETF: 1:5
            open_position(self.p, "GLD", "LONG", leverage=10, margin_amount=Decimal("100"))
        pos = open_position(self.p, "XAUUSD", "LONG", leverage=20, margin_amount=Decimal("100"))
        self.assertEqual(pos.leverage, 20)
        self.assertEqual(open_position(self.p, "EURUSD", "LONG", leverage=30, margin_amount=Decimal("100")).leverage, 30)
        with self.assertRaises(TradingError):  # exótica: 1:20
            open_position(self.p, "USDCOP", "LONG", leverage=30, margin_amount=Decimal("100"))
        with self.assertRaises(TradingError):  # cripto: 1:2
            open_position(self.p, "BTCUSD", "LONG", leverage=5, margin_amount=Decimal("100"))

    def test_usd_base_pair_converts_to_dollars(self):
        # USDJPY: 1.000 USD de margen a 1:10 = 10.000 USD nocionales = 10.000 unidades (dólares)
        pos = open_position(self.p, "USDJPY", "LONG", leverage=10, margin_amount=Decimal("1000"))
        self.assertAlmostEqual(float(pos.quantity), 10000, delta=2)
        self.assertAlmostEqual(float(pos.notional), 10000, delta=2)
        inst = self._move("USDJPY", 1.01)  # el dólar sube 1 % frente al yen
        pos.refresh_from_db()
        pos.instrument = inst
        # ganancia ≈ 1 % del nocional, en USD (≈ 99 tras convertir yenes y restar spread)
        self.assertAlmostEqual(float(pos.unrealized_pnl()), 98, delta=3)

    def test_api_accepts_forex_leverage_30(self):
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post(f"/api/portfolios/{self.p.id}/positions/",
                   {"symbol": "EURUSD", "side": "LONG", "leverage": 30, "margin_amount": "500.00", "take_profit": None}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["leverage"], 30)
        self.assertEqual(r.data["quote_currency"], "USD")

    def test_withdraw_limited_to_free_margin(self):
        from portfolios.services import TradeError, withdraw
        open_position(self.p, "SPY", "LONG", 5, margin_amount=Decimal("6000"))
        self._move("SPY", 0.95)  # pérdida flotante ≈ 1.500: libre ≈ 4.000 − 1.500
        with self.assertRaises(TradeError):
            withdraw(self.p, Decimal("4000"))
        withdraw(self.p, Decimal("1000"))

    def test_double_close_is_harmless(self):
        pos = open_position(self.p, "SPY", "LONG", 2, margin_amount=Decimal("1000"))
        close_position(pos)
        with self.assertRaises(TradingError):
            close_position(pos)
        self.p.refresh_from_db()
        self.assertLess(self.p.cash, Decimal("10001"))  # no se acreditó dos veces

    def test_forex_cannot_be_bought_spot(self):
        from portfolios.services import TradeError
        with self.assertRaises(TradeError):
            execute_trade(self.p, "EURUSD", "BUY", amount=Decimal("500"))

    def test_leverage_multiplies_profit(self):
        pos = open_position(self.p, "SPY", "LONG", leverage=5, margin_amount=Decimal("1000"))
        self._move("SPY", 1.02)
        pos.refresh_from_db()
        pnl = pos.unrealized_pnl()
        self.assertGreater(pnl, Decimal("80"))  # ≈ 2 % × 5 000 − spread ≈ 97

    def test_short_gains_when_price_falls(self):
        pos = open_position(self.p, "SPY", "SHORT", leverage=2, margin_amount=Decimal("1000"))
        self._move("SPY", 0.97)
        closed = close_position(pos)
        self.assertGreater(closed.realized_pnl, 0)

    def test_protection_must_be_on_correct_side(self):
        price = self.insts["SPY"].current_price
        with self.assertRaises(TradingError):
            open_position(self.p, "SPY", "LONG", 1, margin_amount=Decimal("500"), take_profit=price * Decimal("0.9"))
        with self.assertRaises(TradingError):
            open_position(self.p, "SPY", "SHORT", 1, margin_amount=Decimal("500"), stop_loss=price * Decimal("0.9"))

    def test_take_profit_closes_position(self):
        price = self.insts["SPY"].current_price
        pos = open_position(self.p, "SPY", "LONG", 5, margin_amount=Decimal("1000"), take_profit=price * Decimal("1.01"))
        inst = self._move("SPY", 1.03)
        check_triggers(inst)
        pos.refresh_from_db()
        self.assertEqual(pos.status, "CLOSED")
        self.assertEqual(pos.close_reason, "TP")
        self.assertEqual(pos.close_price, pos.take_profit)

    def test_stop_loss_closes_position(self):
        price = self.insts["SPY"].current_price
        pos = open_position(self.p, "SPY", "LONG", 5, margin_amount=Decimal("1000"), stop_loss=price * Decimal("0.99"))
        inst = self._move("SPY", 0.985)
        check_triggers(inst)
        pos.refresh_from_db()
        self.assertEqual(pos.close_reason, "SL")
        self.assertLess(pos.realized_pnl, 0)

    def test_stop_out_and_negative_balance_protection(self):
        # Todo el efectivo como margen 1:5: una caída de 15 % lleva el nivel de margen bajo 50 %
        pos = open_position(self.p, "SPY", "LONG", 5, margin_amount=Decimal("9990"))
        inst = self._move("SPY", 0.85)
        check_triggers(inst)
        pos.refresh_from_db()
        self.assertEqual(pos.close_reason, "STOP_OUT")
        self.p.refresh_from_db()
        self.assertGreaterEqual(self.p.cash, Decimal("0"))

    def test_spot_stop_loss_sells_holding(self):
        price = self.insts["AAPL"].current_price
        execute_trade(self.p, "AAPL", "BUY", amount=Decimal("1000"), stop_loss=price * Decimal("0.95"))
        inst = self._move("AAPL", 0.9)
        check_triggers(inst)
        self.assertFalse(self.p.holdings.exists())
        self.assertEqual(self.p.transactions.filter(type="SELL").first().note, "Stop loss")

    def test_valuation_includes_margin_positions(self):
        open_position(self.p, "SPY", "LONG", 5, margin_amount=Decimal("1000"))
        v = valuate_portfolio(self.p)
        self.assertAlmostEqual(float(v["total_value"]), 10000, delta=10)  # solo pierde el spread
        self.assertEqual(margin_status(self.p)["open_positions"], 1)

    def test_api_open_and_close(self):
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post(f"/api/portfolios/{self.p.id}/positions/", {"symbol": "SPY", "side": "LONG", "leverage": 3, "margin_amount": 500}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        r = c.post(f"/api/positions/{r.data['id']}/close/")
        self.assertEqual(r.data["status"], "CLOSED")
        other = get_user_model().objects.create_user("x9", "x9@uis.edu.co", "Demo12345!")
        c.force_authenticate(other)
        self.assertEqual(c.post(f"/api/positions/{Position.objects.first().id}/close/").status_code, 404)
