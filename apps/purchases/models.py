"""خرید: تأمین‌کننده، فاکتور خرید، برگشت از خرید."""
from decimal import Decimal

from django.db import models
from django.db.models import Sum

from apps.core.models import CompanyScopedModel


class Supplier(CompanyScopedModel):
    name = models.CharField("نام", max_length=200)
    national_id = models.CharField("شناسه ملی / کد ملی", max_length=11, blank=True)
    economic_code = models.CharField("کد اقتصادی", max_length=20, blank=True)
    supplier_type = models.PositiveSmallIntegerField(
        "نوع تأمین‌کننده", default=1, choices=[(1, "حقیقی"), (2, "حقوقی")],
    )
    postal_code = models.CharField("کد پستی", max_length=10, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "تأمین‌کننده"
        verbose_name_plural = "تأمین‌کنندگان"

    def __str__(self) -> str:
        return self.name


class PurchaseInvoice(CompanyScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        POSTED = "posted", "ثبت‌شده"

    fiscal_year = models.ForeignKey("core.FiscalYear", on_delete=models.PROTECT, related_name="purchase_invoices")
    number = models.CharField("شماره فاکتور", max_length=30)
    date = models.DateField("تاریخ")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    journal = models.ForeignKey("accounting.Journal", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")

    total_before_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_after_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_vat = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("company", "fiscal_year", "number")]
        ordering = ["-date", "-id"]
        verbose_name = "فاکتور خرید"
        verbose_name_plural = "فاکتورهای خرید"

    def __str__(self) -> str:
        return f"{self.number} — {self.supplier.name}"

    def recalc_totals(self):
        b = d = a = v = Decimal("0")
        for line in self.lines.all():
            line.recalc()
            line.save(update_fields=["before_discount", "after_discount", "vat_amount", "total"])
            b += line.before_discount
            d += line.discount
            a += line.after_discount
            v += line.vat_amount
        self.total_before_discount = b
        self.total_discount = d
        self.total_after_discount = a
        self.total_vat = v
        self.total_amount = a + v
        self.save(update_fields=[
            "total_before_discount", "total_discount",
            "total_after_discount", "total_vat", "total_amount",
        ])


class PurchaseInvoiceLine(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("sales.Product", on_delete=models.PROTECT)
    warehouse = models.ForeignKey(
        "inventory.Warehouse", null=True, blank=True, on_delete=models.PROTECT,
        related_name="+", verbose_name="انبار",
    )
    quantity = models.DecimalField(max_digits=20, decimal_places=3, default=Decimal("1"))
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    vat_rate = models.PositiveSmallIntegerField(default=10)

    before_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    after_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    vat_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    unit_cost = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "id"]

    def recalc(self):
        self.before_discount = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        self.after_discount = (self.before_discount - self.discount).quantize(Decimal("0.01"))
        self.vat_amount = (self.after_discount * Decimal(self.vat_rate) / Decimal(100)).quantize(Decimal("0.01"))
        self.total = self.after_discount + self.vat_amount


class PurchaseReturn(CompanyScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        POSTED = "posted", "ثبت‌شده"

    fiscal_year = models.ForeignKey("core.FiscalYear", on_delete=models.PROTECT, related_name="purchase_returns")
    number = models.CharField("شماره برگشت", max_length=30)
    date = models.DateField("تاریخ")
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.PROTECT, related_name="returns")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    journal = models.ForeignKey("accounting.Journal", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")

    total_before_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_after_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_vat = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("company", "fiscal_year", "number")]
        ordering = ["-date", "-id"]
        verbose_name = "برگشت از خرید"
        verbose_name_plural = "برگشت‌های از خرید"

    def __str__(self) -> str:
        return f"PR {self.number} ← {self.invoice.number}"

    def recalc_totals(self):
        b = d = a = v = Decimal("0")
        for line in self.lines.all():
            line.recalc()
            line.save(update_fields=["before_discount", "after_discount", "vat_amount", "total"])
            b += line.before_discount
            d += line.discount
            a += line.after_discount
            v += line.vat_amount
        self.total_before_discount = b
        self.total_discount = d
        self.total_after_discount = a
        self.total_vat = v
        self.total_amount = a + v
        self.save(update_fields=[
            "total_before_discount", "total_discount",
            "total_after_discount", "total_vat", "total_amount",
        ])


class PurchaseReturnLine(models.Model):
    return_doc = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name="lines")
    original_line = models.ForeignKey(PurchaseInvoiceLine, on_delete=models.PROTECT, related_name="return_lines")
    product = models.ForeignKey("sales.Product", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=20, decimal_places=3, default=Decimal("0"))
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    vat_rate = models.PositiveSmallIntegerField(default=10)

    before_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    after_discount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    vat_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "id"]

    def recalc(self):
        self.before_discount = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        self.after_discount = (self.before_discount - self.discount).quantize(Decimal("0.01"))
        self.vat_amount = (self.after_discount * Decimal(self.vat_rate) / Decimal(100)).quantize(Decimal("0.01"))
        self.total = self.after_discount + self.vat_amount

    def already_returned(self) -> Decimal:
        qs = PurchaseReturnLine.objects.filter(
            original_line=self.original_line,
            return_doc__status=PurchaseReturn.Status.POSTED,
        ).exclude(pk=self.pk)
        return qs.aggregate(s=Sum("quantity"))["s"] or Decimal("0")

    def max_returnable(self) -> Decimal:
        return self.original_line.quantity - self.already_returned()