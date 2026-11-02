from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.models import Company, FiscalYear
from .models import Account, Journal, JournalEntry
from .services import trial_balance

class JournalPostingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test", national_id="12345678901")
        self.fy = FiscalYear.objects.create(
            company=self.company, name="1403",
            start_date=date(2024, 3, 20), end_date=date(2025, 3, 20),
        )
        self.cash = Account.objects.create(company=self.company, code="110101", name="صندوق", account_type="ASSET")
        self.rev = Account.objects.create(company=self.company, code="4101", name="فروش", account_type="REVENUE")

    def _journal(self):
        j = Journal.objects.create(
            company=self.company, fiscal_year=self.fy, number="00001",
            date=date(2024, 6, 1), description="test",
        )
        JournalEntry.objects.create(journal=j, account=self.cash, debit=Decimal("1000"))
        JournalEntry.objects.create(journal=j, account=self.rev, credit=Decimal("1000"))
        return j

    def test_balanced_journal_posts(self):
        j = self._journal()
        j.post()
        self.assertTrue(j.is_posted)

    def test_unbalanced_journal_rejected(self):
        j = self._journal()
        j.entries.filter(account=self.rev).update(credit=Decimal("900"))
        with self.assertRaises(ValidationError):
            j.post()

    def test_posted_journal_cannot_be_deleted(self):
        j = self._journal()
        j.post()
        with self.assertRaises(ValidationError):
            j.delete()

    def test_trial_balance_is_balanced(self):
        j = self._journal()
        j.post()
        rows, d, c = trial_balance(self.fy)
        self.assertEqual(d, c)
