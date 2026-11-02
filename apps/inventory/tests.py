from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.models import Company
from apps.sales.models import Product
from .models import StockBalance, Warehouse
from .services import issue_stock, receive_stock

class WeightedAverageCostTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test", national_id="12345678901")
        self.warehouse = Warehouse.objects.create(company=self.company, code="MAIN", name="انبار اصلی")
        self.product = Product.objects.create(
            company=self.company, code="1001", name="کالای تست",
            unit="عدد", unit_price=Decimal("1000"), vat_rate=10,
        )

    def test_first_receipt_sets_avg_cost(self):
        receive_stock(warehouse=self.warehouse, product=self.product,
                      qty=10, unit_cost=Decimal("100"), date=date(2024, 6, 1))
        bal = StockBalance.objects.get(warehouse=self.warehouse, product=self.product)
        self.assertEqual(bal.quantity, Decimal("10"))
        self.assertEqual(bal.avg_cost, Decimal("100.0000"))
        self.assertEqual(bal.total_value, Decimal("1000.00"))

    def test_second_receipt_updates_weighted_average(self):
        receive_stock(warehouse=self.warehouse, product=self.product,
                      qty=10, unit_cost=Decimal("100"), date=date(2024, 6, 1))
        receive_stock(warehouse=self.warehouse, product=self.product,
                      qty=10, unit_cost=Decimal("200"), date=date(2024, 6, 2))
        bal = StockBalance.objects.get(warehouse=self.warehouse, product=self.product)
        self.assertEqual(bal.quantity, Decimal("20"))
        self.assertEqual(bal.avg_cost, Decimal("150.0000"))

    def test_issue_uses_current_avg_cost(self):
        receive_stock(warehouse=self.warehouse, product=self.product,
                      qty=10, unit_cost=Decimal("100"), date=date(2024, 6, 1))
        move = issue_stock(warehouse=self.warehouse, product=self.product,
                           qty=4, date=date(2024, 6, 5))
        self.assertEqual(move.unit_cost, Decimal("100.0000"))
        self.assertEqual(move.total_cost, Decimal("400.00"))

    def test_issue_more_than_available_rejected(self):
        receive_stock(warehouse=self.warehouse, product=self.product,
                      qty=5, unit_cost=Decimal("100"), date=date(2024, 6, 1))
        with self.assertRaises(ValidationError):
            issue_stock(warehouse=self.warehouse, product=self.product,
                        qty=10, date=date(2024, 6, 2))

    def test_full_issue_zeroes_balance(self):
        receive_stock(warehouse=self.warehouse, product=self.product,
                      qty=3, unit_cost=Decimal("33.33"), date=date(2024, 6, 1))
        issue_stock(warehouse=self.warehouse, product=self.product, qty=3, date=date(2024, 6, 5))
        bal = StockBalance.objects.get(warehouse=self.warehouse, product=self.product)
        self.assertEqual(bal.quantity, Decimal("0"))
        self.assertEqual(bal.total_value, Decimal("0.00"))
