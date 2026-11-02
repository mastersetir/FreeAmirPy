"""مدل‌های مشترک: شرکت و سال مالی."""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .mixins import CompanyScopedModel, FiscalYearScopedModel  # noqa: F401 (re-export)

__all__ = ["Company", "FiscalYear", "CompanyScopedModel", "FiscalYearScopedModel"]

class Company(models.Model):
    """شرکت — واحد اصلی چندمستأجری."""
    class ApprovalPolicy(models.TextChoices):
        NONE = "none", "بدون تأیید"
        JOURNALS = "journals", "فقط اسناد حسابداری"
        ALL = "all", "همه‌ی ثبت‌ها"

    name = models.CharField("نام شرکت", max_length=200)
    legal_name = models.CharField("نام حقوقی", max_length=200, blank=True)
    national_id = models.CharField("شناسه ملی", max_length=11, unique=True)
    economic_code = models.CharField("کد اقتصادی", max_length=20, blank=True)
    registration_number = models.CharField("شماره ثبت", max_length=20, blank=True)
    address = models.TextField("نشانی", blank=True)
    phone = models.CharField("تلفن", max_length=30, blank=True)

    approval_policy = models.CharField(
        "سیاست تأیید", max_length=20,
        choices=ApprovalPolicy.choices, default=ApprovalPolicy.NONE,
        help_text="اگر فعال باشد، اسناد قبل از ثبت نیاز به تأیید دارند.",
    )

    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "شرکت"
        verbose_name_plural = "شرکت‌ها"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def requires_journal_approval(self) -> bool:
        return self.approval_policy in (self.ApprovalPolicy.JOURNALS, self.ApprovalPolicy.ALL)

class FiscalYear(models.Model):
    """سال مالی — دامنه‌ی تمام اسناد حسابداری."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="fiscal_years")
    name = models.CharField("عنوان", max_length=100)
    start_date = models.DateField("تاریخ شروع")
    end_date = models.DateField("تاریخ پایان")
    is_closed = models.BooleanField("بسته شده", default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_journal = models.ForeignKey(
        "accounting.Journal", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
        verbose_name="سند بستن",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "سال مالی"
        verbose_name_plural = "سال‌های مالی"
        unique_together = [("company", "name")]
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.company.name} — {self.name}"

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("تاریخ شروع باید قبل از تاریخ پایان باشد.")
        overlap = FiscalYear.objects.filter(
            company=self.company,
            start_date__lt=self.end_date,
            end_date__gt=self.start_date,
        ).exclude(pk=self.pk)
        if overlap.exists():
            raise ValidationError("بازه‌ی این سال مالی با سال مالی دیگر همپوشانی دارد.")

    def close(self, user=None):
        from apps.accounting.closing import close_fiscal_year
        return close_fiscal_year(self, user=user)
