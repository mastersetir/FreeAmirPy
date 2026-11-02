"""Seed Iranian payroll tax brackets for a given year."""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.hr.models import TaxBracket

DEFAULT_1403 = [
    (1, Decimal("0"),        Decimal("12000000"),  Decimal("0")),
    (2, Decimal("12000000"), Decimal("16500000"),  Decimal("10")),
    (3, Decimal("16500000"), Decimal("27000000"),  Decimal("15")),
    (4, Decimal("27000000"), Decimal("36000000"),  Decimal("20")),
    (5, Decimal("36000000"), None,                 Decimal("30")),
]

DEFAULT_1404 = [
    (1, Decimal("0"),        Decimal("24000000"),  Decimal("0")),
    (2, Decimal("24000000"), Decimal("33000000"),  Decimal("10")),
    (3, Decimal("33000000"), Decimal("54000000"),  Decimal("15")),
    (4, Decimal("54000000"), Decimal("72000000"),  Decimal("20")),
    (5, Decimal("72000000"), None,                 Decimal("30")),
]

class Command(BaseCommand):
    help = "Seed tax brackets for a specific year."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, year, force, **kwargs):
        if TaxBracket.objects.filter(year=year).exists() and not force:
            self.stdout.write(self.style.WARNING(f"Brackets for {year} exist. Use --force."))
            return
        data = DEFAULT_1403 if year == 1403 else DEFAULT_1404 if year == 1404 else DEFAULT_1403
        TaxBracket.objects.filter(year=year).delete()
        for order, mn, mx, rate in data:
            TaxBracket.objects.create(year=year, order=order, min_amount=mn, max_amount=mx, rate=rate)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(data)} brackets for year {year}."))
