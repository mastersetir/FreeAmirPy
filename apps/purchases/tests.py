from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounting.models import Account
from apps.core.models import Company, FiscalYear
from apps.inventory.models import StockBalance, Warehouse
from apps.sales.models import Product

from .models import PurchaseInvoice, PurchaseInvoiceLine, PurchaseReturn, Supplier
from .services import build_purchase_return_lines, post_purchase_invoice, post_purchase_return

class PurchaseTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test", national_id="12345678901")
        self.fy = FiscalYear.objects.create(
            company=self.company, name="1403",
            start_date=date(2024, 3, 20), end_date=date(2025, 3, 20),
        )
        self.supplier = Supplier.objects.create(company=self.company, name="تأمین‌کننده تست")
        self.product = Product.objects.create(
            company=self.company, code="P1", name="کالا",
            unit="عدد", unit_price=Decimal("1000"), vat_rate=10,
        )
        self.warehouse = Warehouse.objects.create(company=self.company, code="MAIN", name="اصلی")
        for code, name, atype in [
            ("1103", "Inventory", "ASSET"), ("2101", "AP", "LIABILITY"),
            ("2102", "VAT", "LIABILITY"), ("5101", "COGS", "EXPENSE"),
        ]:
            Account.objects.create(company=self.company, code=code, name=name, account_type=atype)

    def _create_invoice(self, qty=10, unit_price=Decimal("100")):
        inv = PurchaseInvoice.objects.create(
            company=self.company, fiscal_year=self.fy,
            number="00001", date=date(2024, 6, 1), supplier=self.supplier,
        )
        PurchaseInvoiceLine.objects.create(
            invoice=inv, product=self.product, warehouse=self.warehouse,
            quantity=qty, unit_price=unit_price, discount=Decimal("0"), vat_rate=10, sequence=1,
        )
        inv.recalc_totals()
        return inv

    def test_posting_purchase_receives_stock(self):
        inv = self._create_invoice(qty=10, unit_price=Decimal("100"))
        journal = post_purchase_invoice(inv)
        self.assertTrue(journal.is_posted)
        bal = StockBalance.objects.get(warehouse=self.warehouse, product=self.product)
        self.assertEqual(bal.quantity, Decimal("10"))
        self.assertEqual(bal.avg_cost, Decimal("100.0000"))

    def test_purchase_return_issues_stock(self):
        inv = self._create_invoice(qty=10, unit_price=Decimal("100"))
        post_purchase_invoice(inv)
        ret = PurchaseReturn.objects.create(
            company=self.company, fiscal_year=self.fy, number="00001",
            date=date(2024, 6, 10), invoice=inv,
        )
        build_purchase_return_lines(ret)
        line = ret.lines.first(); line.quantity = Decimal("3"); line.save(); ret.recalc_totals()
        post_purchase_return(ret)
        bal = StockBalance.objects.get(warehouse=self.warehouse, product=self.product)
        self.assertEqual(bal.quantity, Decimal("7"))

    def test_return_rejects_excess(self):
        inv = self._create_invoice(qty=10, unit_price=Decimal("100"))
        post_purchase_invoice(inv)
        ret = PurchaseReturn.objects.create(
            company=self.company, fiscal_year=self.fy, number="00001",
            date=date(2024, 6, 10), invoice=inv,
        )
        build_purchase_return_lines(ret)
        line = ret.lines.first(); line.quantity = Decimal("100"); line.save(); ret.recalc_totals()
        with self.assertRaises(ValidationError):
            post_purchase_return(ret)
