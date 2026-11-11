from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from market.testing import make_instruments
from portfolios.services import TradeError, create_portfolio, execute_trade, valuate_portfolio


class PortfolioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.insts = make_instruments(("SPY", "AAPL", "KO", "AGG"))

    def setUp(self):
        self.user = get_user_model().objects.create_user("inv", "inv@uis.edu.co", "Demo12345!")
        self.p = create_portfolio(self.user, "Principal", Decimal("10000"))

    def test_create_portfolio_moves_cash_from_profile(self):
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.cash_balance, Decimal("90000.00"))
        self.assertEqual(self.p.cash, Decimal("10000.00"))

    def test_buy_charges_commission_and_updates_holding(self):
        tx = execute_trade(self.p, "KO", "BUY", quantity=Decimal("10"))
        self.p.refresh_from_db()
        gross = (Decimal("10") * tx.price).quantize(Decimal("0.01"))  # precio realmente ejecutado
        self.assertEqual(tx.fee, Decimal("1.00"))  # 0,1 % < mínimo de 1 USD
        self.assertEqual(self.p.cash, Decimal("10000") - gross - Decimal("1.00"))
        self.assertEqual(self.p.holdings.get().quantity, Decimal("10"))

    def test_buy_by_amount_never_exceeds_amount(self):
        execute_trade(self.p, "AAPL", "BUY", amount=Decimal("1000"))
        self.p.refresh_from_db()
        self.assertGreaterEqual(self.p.cash, Decimal("9000"))

    def test_cannot_buy_without_funds(self):
        with self.assertRaises(TradeError):
            execute_trade(self.p, "SPY", "BUY", quantity=Decimal("1000"))

    def test_cannot_sell_more_than_owned(self):
        execute_trade(self.p, "KO", "BUY", quantity=Decimal("5"))
        with self.assertRaises(TradeError):
            execute_trade(self.p, "KO", "SELL", quantity=Decimal("6"))

    def test_sell_all_removes_holding_and_records_realized_pnl(self):
        execute_trade(self.p, "KO", "BUY", quantity=Decimal("5"))
        tx = execute_trade(self.p, "KO", "SELL", quantity=Decimal("5"))
        self.assertFalse(self.p.holdings.exists())
        self.assertIsNotNone(tx.realized_pnl)

    def test_valuation_totals(self):
        execute_trade(self.p, "SPY", "BUY", amount=Decimal("3000"))
        execute_trade(self.p, "AGG", "BUY", amount=Decimal("2000"))
        v = valuate_portfolio(self.p)
        self.assertEqual(v["total_value"], v["cash"] + v["invested_value"])
        self.assertAlmostEqual(float(sum(h["weight"] for h in v["holdings"])) + float(v["cash"] / v["total_value"] * 100), 100, delta=0.1)

    def test_api_trade_and_detail(self):
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post(f"/api/portfolios/{self.p.id}/trade/", {"symbol": "AAPL", "side": "BUY", "amount": 500}, format="json")
        self.assertEqual(r.status_code, 201)
        r = c.get(f"/api/portfolios/{self.p.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("risk", r.data)
        self.assertTrue(r.data["insights"])

    def test_users_cannot_see_other_portfolios(self):
        other = get_user_model().objects.create_user("otro", "o@uis.edu.co", "Demo12345!")
        c = APIClient()
        c.force_authenticate(other)
        self.assertEqual(c.get(f"/api/portfolios/{self.p.id}/").status_code, 404)

    def test_closing_portfolio_returns_cash(self):
        c = APIClient()
        c.force_authenticate(self.user)
        c.post(f"/api/portfolios/{self.p.id}/trade/", {"symbol": "KO", "side": "BUY", "quantity": 3}, format="json")
        r = c.delete(f"/api/portfolios/{self.p.id}/")
        self.assertEqual(r.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertGreater(self.user.profile.cash_balance, Decimal("99990"))
