from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company, FiscalYear
from apps.purchases.models import PurchaseInvoice, PurchaseInvoiceLine, Supplier
from apps.sales.models import Customer, Product, SaleInvoice, SaleInvoiceLine

from .client import (
    INS_PURCHASE, INS_SALE, INTY_NORMAL,
    build_invoice_body, build_invoice_header,
)
from .models import MoadianConfig

class HeaderBuilderTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="شرکت تست", national_id="12345678901", economic_code="EC123",
            registration_number="REG1",
        )
        self.fy = FiscalYear.objects.create(
            company=self.company, name="1403",
            start_date=date(2024, 3, 20), end_date=date(2025, 3, 20),
        )
        self.customer = Customer.objects.create(
            company=self.company, name="مشتری", national_id="98765432109",
            economic_code="EC987", customer_type=2,
        )
        self.product = Product.objects.create(
            company=self.company, code="P1", name="کالا", unit="عدد",
            unit_price=Decimal("1000"), vat_rate=10,
        )
        self.config = MoadianConfig(
            company=self.company, tax_id="TAX123", client_id="cid",
            client_secret="csec", private_key="", environment="sandbox",
        )
        self.sale = SaleInvoice.objects.create(
            company=self.company, fiscal_year=self.fy, number="00001",
            date=date(2024, 6, 1), customer=self.customer, settlement_method=1,
        )
        SaleInvoiceLine.objects.create(
            invoice=self.sale, product=self.product, quantity=Decimal("2"),
            unit_price=Decimal("1000"), discount=Decimal("0"), vat_rate=10, sequence=1,
        )
        self.sale.recalc_totals()

    def test_sale_header_semantics(self):
        header = build_invoice_header(config=self.config, document=self.sale, document_type="sale_invoice")
        self.assertEqual(header["inty"], INTY_NORMAL)
        self.assertEqual(header["ins"], INS_SALE)
        self.assertEqual(header["inp"], 1)
        self.assertEqual(header["tins"], "12345678901")
        self.assertEqual(header["bid"], "98765432109")
        self.assertEqual(header["tob"], 2)
        self.assertEqual(header["indatim"], header["indati2m"])

    def test_purchase_header_inverts_parties(self):
        supplier = Supplier.objects.create(
            company=self.company, name="تأمین", national_id="11122233344",
            economic_code="SUPEC", supplier_type=2,
        )
        inv = PurchaseInvoice.objects.create(
            company=self.company, fiscal_year=self.fy, number="P001",
            date=date(2024, 6, 2), supplier=supplier,
        )
        PurchaseInvoiceLine.objects.create(
            invoice=inv, product=self.product, quantity=Decimal("5"),
            unit_price=Decimal("100"), discount=Decimal("0"), vat_rate=10, sequence=1,
        )
        inv.recalc_totals()
        header = build_invoice_header(config=self.config, document=inv, document_type="purchase_invoice")
        self.assertEqual(header["ins"], INS_PURCHASE)
        self.assertEqual(header["tins"], "11122233344")
        self.assertEqual(header["bid"], "12345678901")

    def test_body_fields(self):
        body = build_invoice_body(self.sale, "sale_invoice")
        self.assertEqual(len(body), 1)
        for key in ("sstid", "sstt", "mu", "am", "fee", "prdis", "dis",
                    "adis", "vra", "vam", "tsstam"):
            self.assertIn(key, body[0])
