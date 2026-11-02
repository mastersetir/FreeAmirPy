"""مدل‌های انبار و بهای تمام‌شده میانگین موزون."""
from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel

class Warehouse(CompanyScopedModel):
    name = models.CharField("نام انبار", max_length=100)
    code = models.CharField("کد انبار", max_length=20)
    address = models.TextField("نشانی", blank=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        unique_together = [("company", "code")]
        verbose_name = "انبار"
        verbose_name_plural = "انبارها"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

class StockMove(CompanyScopedModel):
    class MoveType(models.TextChoices):
        IN = "in", "ورود"
        OUT = "out", "خروج"
        ADJUST = "adjust", "تعدیل"

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="moves")
    product = models.ForeignKey("sales.Product", on_delete=models.PROTECT, related_name="stock_moves")
    move_type = models.CharField(max_length=10, choices=MoveType.choices)
    quantity = models.DecimalField("مقدار", max_digits=20, decimal_places=3)
    unit_cost = models.DecimalField("بهای واحد", max_digits=20, decimal_places=4, default=Decimal("0"))
    total_cost = models.DecimalField("بهای کل", max_digits=20, decimal_places=2, default=Decimal("0"))
    date = models.DateField("تاریخ")
    reference = models.CharField("مرجع", max_length=100, blank=True)
    note = models.TextField("توضیحات", blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "گردش موجودی"
        verbose_name_plural = "گردش موجودی"
        indexes = [models.Index(fields=["warehouse", "product", "date"])]

    def __str__(self) -> str:
        return f"{self.get_move_type_display()} {self.quantity} × {self.product}"

class StockBalance(CompanyScopedModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="balances")
    product = models.ForeignKey("sales.Product", on_delete=models.PROTECT, related_name="stock_balances")
    quantity = models.DecimalField("موجودی", max_digits=20, decimal_places=3, default=Decimal("0"))
    avg_cost = models.DecimalField("بهای میانگین", max_digits=20, decimal_places=4, default=Decimal("0"))
    total_value = models.DecimalField("ارزش موجودی", max_digits=20, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = [("warehouse", "product")]
        verbose_name = "مانده موجودی"
        verbose_name_plural = "مانده‌های موجودی"

    def __str__(self) -> str:
        return f"{self.warehouse.code}/{self.product.code}: {self.quantity}"
