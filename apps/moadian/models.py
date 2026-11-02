"""مدل‌های سامانه مودیان: تنظیمات، فاکتور ارسالی (۴ نوع)، لاگ."""
from django.db import models

from apps.core.models import CompanyScopedModel

class MoadianConfig(CompanyScopedModel):
    class Environment(models.TextChoices):
        SANDBOX = "sandbox", "محیط تست"
        PRODUCTION = "production", "محیط عملیاتی"

    tax_id = models.CharField("شناسه یکتای حافظه مالیاتی", max_length=50)
    client_id = models.CharField("Client ID", max_length=200)
    client_secret = models.CharField("Client Secret", max_length=200)
    private_key = models.TextField("کلید خصوصی (PEM)")
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.SANDBOX)
    is_active = models.BooleanField(default=True)

    cached_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "تنظیمات مودیان"
        verbose_name_plural = "تنظیمات مودیان"
        unique_together = [("company",)]

    def __str__(self) -> str:
        return f"{self.company.name} — {self.get_environment_display()}"

class MoadianInvoice(CompanyScopedModel):
    class DocumentType(models.TextChoices):
        SALE_INVOICE = "sale_invoice", "فاکتور فروش"
        SALE_RETURN = "sale_return", "برگشت از فروش"
        PURCHASE_INVOICE = "purchase_invoice", "فاکتور خرید"
        PURCHASE_RETURN = "purchase_return", "برگشت از خرید"

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار ارسال"
        SENT = "sent", "ارسال شد"
        SUCCESS = "success", "تأیید شد"
        FAILED = "failed", "خطا"
        REJECTED = "rejected", "رد شد"

    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    document_id = models.PositiveBigIntegerField()
    document_repr = models.CharField(max_length=200, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reference_number = models.CharField("شماره مرجع", max_length=100, blank=True)
    tax_id = models.CharField("شناسه یکتای مالیاتی", max_length=100, blank=True)
    request_payload = models.JSONField("Payload ارسالی", null=True, blank=True)
    response_payload = models.JSONField("پاسخ", null=True, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "فاکتور مودیان"
        verbose_name_plural = "فاکتورهای مودیان"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["document_type", "document_id"])]

    def __str__(self) -> str:
        return f"{self.get_document_type_display()} #{self.document_repr} — {self.get_status_display()}"

    def get_document(self):
        from apps.sales.models import SaleInvoice, SaleReturn
        from apps.purchases.models import PurchaseInvoice, PurchaseReturn
        models_map = {
            self.DocumentType.SALE_INVOICE: SaleInvoice,
            self.DocumentType.SALE_RETURN: SaleReturn,
            self.DocumentType.PURCHASE_INVOICE: PurchaseInvoice,
            self.DocumentType.PURCHASE_RETURN: PurchaseReturn,
        }
        return models_map[self.document_type].objects.filter(pk=self.document_id).first()

class MoadianLog(models.Model):
    config = models.ForeignKey(MoadianConfig, on_delete=models.CASCADE, related_name="logs")
    endpoint = models.CharField(max_length=300)
    method = models.CharField(max_length=10)
    request_body = models.TextField(blank=True)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "لاگ مودیان"
        verbose_name_plural = "لاگ‌های مودیان"
