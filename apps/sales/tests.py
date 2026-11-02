from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounting.models import Account
from apps.core.models import Company, FiscalYear
from apps.inventory.models import StockBalance, Warehouse
from apps.inventory.services import receive_stock

from .models import Customer, Product, SaleInvoice, SaleInvoiceLine, SaleReturn
from .services import build_sale_return_lines, post_sale_invoice, post_sale_return

class SalePostingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test", national_id="12345678901")
        self.fy = FiscalYear.objects.create(
            company=self.company, name="1403",
            start_date=date(2024, 3, 20), end_date=date(2025, 3, 20),
        )
        self.customer = Customer.objects.create(company=self.company, name="مشتری تست")
        self.product = Product.objects.create(
            company=self.company, code="P1", name="کالای تست",
            unit="عدد", unit_price=Decimal("1000"), vat_rate=10,
        )
        self.warehouse = Warehouse.objects.create(company=self.company, code="MAIN", name="اصلی")
        for code, name, atype in [
            ("110201", "AR", "ASSET"), ("4101", "فروش", "REVENUE"),
            ("2102", "VAT", "LIABILITY"), ("5101", "COGS", "EXPENSE"),
            ("1103", "Inventory", "ASSET"),
        ]:
            Account.objects.create(company=self.company, code=code, name=name, account_type=atype)
        receive_stock(warehouse=self.warehouse, product=self.product,
                      qty=10, unit_cost=Decimal("500"), date=date(2024, 4, 1))

    def _create_invoice(self, qty=4):
        inv = SaleInvoice.objects.create(
            company=self.company, fiscal_year=self.fy,
            number="00001", date=date(2024, 6, 1),
            customer=self.customer, settlement_method=1,
        )
        SaleInvoiceLine.objects.create(
            invoice=inv, product=self.product, quantity=qty,
            unit_price=Decimal("1000"), discount=Decimal("0"), vat_rate=10, sequence=1,
        )
        inv.recalc_totals()
        return inv

    def test_posting_saves_unit_cogs(self):
        inv = self._create_invoice(qty=4)
        post_sale_invoice(inv)
        self.assertEqual(inv.lines.first().unit_cogs, Decimal("500.0000"))

    def test_totals_are_persisted(self):
        inv = self._create_invoice(qty=4)
        # totals from recalc_totals should be saved correctly
        self.assertEqual(inv.total_after_discount, Decimal("4000.00"))
        self.assertEqual(inv.total_vat, Decimal("400.00"))
        self.assertEqual(inv.total_amount, Decimal("4400.00"))

    def test_sale_return_restocks(self):
        inv = self._create_invoice(qty=4)
        post_sale_invoice(inv)
        ret = SaleReturn.objects.create(
            company=self.company, fiscal_year=self.fy, number="00001",
            date=date(2024, 6, 10), invoice=inv,
        )
        build_sale_return_lines(ret)
        line = ret.lines.first()
        line.quantity = Decimal("2"); line.save(); ret.recalc_totals()
        journal, cogs = post_sale_return(ret)
        bal = StockBalance.objects.get(warehouse=self.warehouse, product=self.product)
        self.assertEqual(bal.quantity, Decimal("8"))
        self.assertTrue(journal.is_posted)

    def test_sale_return_rejects_excess(self):
        inv = self._create_invoice(qty=4)
        post_sale_invoice(inv)
        ret = SaleReturn.objects.create(
            company=self.company, fiscal_year=self.fy, number="00001",
            date=date(2024, 6, 10), invoice=inv,
        )
        build_sale_return_lines(ret)
        line = ret.lines.first(); line.quantity = Decimal("100"); line.save(); ret.recalc_totals()
        with self.assertRaises(ValidationError):
            post_sale_return(ret)
