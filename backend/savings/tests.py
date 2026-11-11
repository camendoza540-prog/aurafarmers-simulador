from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from savings.services import (
    SavingsError, account_value, advance_time, calculator, close_account, deposit_to_account, open_account,
    renew_account, savings_summary,
)


class SavingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("aho", "a@uis.edu.co", "Demo12345!")

    def test_compound_interest_formula(self):
        acc = open_account(self.user, "AHORRO", Decimal("10000"))
        advance_time(acc, 365)
        self.assertAlmostEqual(float(account_value(acc)["value"]), 10350.0, delta=1.0)

    def test_cdt_cannot_be_withdrawn_before_maturity(self):
        acc = open_account(self.user, "CDT90", Decimal("1000"))
        with self.assertRaises(SavingsError):
            close_account(acc)
        advance_time(acc, 90)
        value = close_account(acc)
        self.assertGreater(value, Decimal("1000"))

    def test_cdt_stops_accruing_after_maturity(self):
        acc = open_account(self.user, "CDT90", Decimal("1000"))
        advance_time(acc, 90)
        at_maturity = account_value(acc)["value"]
        advance_time(acc, 300)
        self.assertEqual(account_value(acc)["value"], at_maturity)

    def test_calculator_matches_closed_formula(self):
        r = calculator(10000, 0, 0.09, 10)
        self.assertAlmostEqual(r["final_balance"], 10000 * 1.09 ** 10, delta=0.5)
        self.assertGreater(r["final_balance"], r["final_simple"])

    def test_nominal_rate_conversion(self):
        r = calculator(1000, 0, 0.09, 1, rate_type="NOMINAL", periods_per_year=12)
        self.assertAlmostEqual(r["effective_annual"], 9.3807, places=3)

    def test_deposit_to_savings_keeps_accrued_interest(self):
        acc = open_account(self.user, "AHORRO", Decimal("1000"))
        advance_time(acc, 365)
        deposit_to_account(acc, Decimal("500"))
        acc.refresh_from_db()
        self.assertEqual(acc.principal, Decimal("1500.00"))
        self.assertAlmostEqual(float(account_value(acc)["value"]), 1535.0, delta=0.5)

    def test_cdt_rejects_deposits_and_early_renewal(self):
        acc = open_account(self.user, "CDT180", Decimal("1000"))
        with self.assertRaises(SavingsError):
            deposit_to_account(acc, Decimal("100"))
        with self.assertRaises(SavingsError):
            renew_account(acc)

    def test_renew_reinvests_capital_and_interest(self):
        acc = open_account(self.user, "CDT90", Decimal("2000"))
        advance_time(acc, 90)
        expected = account_value(acc)["value"]
        new = renew_account(acc)
        self.assertEqual(new.principal, expected)
        self.assertEqual(new.term_days, 90)
        self.assertEqual(savings_summary(self.user)["accounts"], 1)

    def test_minimum_amount_and_insufficient_cash(self):
        with self.assertRaises(SavingsError):
            open_account(self.user, "CDT360", Decimal("100"))
        with self.assertRaises(SavingsError):
            open_account(self.user, "AHORRO", Decimal("200000"))
