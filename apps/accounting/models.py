"""هسته‌ی حسابداری دوبل: حساب، سند، آرتیکل."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import CompanyScopedModel, FiscalYear

class AccountType(models.TextChoices):
    ASSET = "ASSET", "دارایی"
    LIABILITY = "LIABILITY", "بدهی"
    EQUITY = "EQUITY", "سرمایه"
    REVENUE = "REVENUE", "درآمد"
    EXPENSE = "EXPENSE", "هزینه"

NORMAL_BALANCE = {
    AccountType.ASSET: "debit",
    AccountType.EXPENSE: "debit",
    AccountType.LIABILITY: "credit",
    AccountType.EQUITY: "credit",
    AccountType.REVENUE: "credit",
}

class Account(CompanyScopedModel):
    code = models.CharField("کد حساب", max_length=20)
    name = models.CharField("نام حساب", max_length=200)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_postable = models.BooleanField("قابل ثبت", default=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        unique_together = [("company", "code")]
        ordering = ["code"]
        verbose_name = "حساب"
        verbose_name_plural = "حساب‌ها"

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    @property
    def normal_balance(self) -> str:
        return NORMAL_BALANCE.get(self.account_type, "debit")

    def save(self, *args, **kwargs):
        if self.pk and self.children.exists():
            self.is_postable = False
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.journal_entries.exists():
            raise ValidationError("این حساب آرتیکل دارد و قابل حذف نیست.")
        if self.children.exists():
            raise ValidationError("این حساب زیرحساب دارد و قابل حذف نیست.")
        super().delete(*args, **kwargs)

class Journal(CompanyScopedModel):
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, related_name="journals")
    number = models.CharField("شماره سند", max_length=30)
    date = models.DateField("تاریخ")
    description = models.TextField("شرح")
    is_posted = models.BooleanField("ثبت شده", default=False)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="+")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        unique_together = [("company", "fiscal_year", "number")]
        ordering = ["-date", "-id"]
        verbose_name = "سند"
        verbose_name_plural = "اسناد"

    def __str__(self) -> str:
        return f"{self.number} — {self.date}"

    @property
    def total_debit(self) -> Decimal:
        return sum((e.debit for e in self.entries.all()), Decimal("0"))

    @property
    def total_credit(self) -> Decimal:
        return sum((e.credit for e in self.entries.all()), Decimal("0"))

    def clean(self):
        if self.fiscal_year_id and not (self.fiscal_year.start_date <= self.date <= self.fiscal_year.end_date):
            raise ValidationError("تاریخ سند خارج از بازه‌ی سال مالی است.")

    @transaction.atomic
    def post(self, user=None):
        if self.is_posted:
            raise ValidationError("این سند قبلاً ثبت شده است.")
        if self.fiscal_year.is_closed:
            raise ValidationError("سال مالی بسته شده است.")

        if self.company.requires_journal_approval:
            from apps.core.approval import has_approved
            if not has_approved(self):
                raise ValidationError(
                    "این شرکت سیاست تأیید دارد. ابتدا باید سند توسط مدیر تأیید شود."
                )

        entries = list(self.entries.select_related("account"))
        if len(entries) < 2:
            raise ValidationError("سند باید حداقل دو آرتیکل داشته باشد.")

        total_debit = sum((e.debit for e in entries), Decimal("0"))
        total_credit = sum((e.credit for e in entries), Decimal("0"))
        if total_debit != total_credit:
            raise ValidationError(
                f"جمع بدهکار ({total_debit}) با جمع بستانکار ({total_credit}) برابر نیست."
            )
        if total_debit <= 0:
            raise ValidationError("جمع سند باید بزرگ‌تر از صفر باشد.")

        for e in entries:
            if e.debit < 0 or e.credit < 0:
                raise ValidationError("مبلغ آرتیکل نمی‌تواند منفی باشد.")
            if e.debit > 0 and e.credit > 0:
                raise ValidationError("یک آرتیکل نمی‌تواند هم‌زمان بدهکار و بستانکار باشد.")
            if not e.account.is_postable:
                raise ValidationError(f"حساب {e.account.code} قابل ثبت نیست (حساب کل است).")
            if e.account.company_id != self.company_id:
                raise ValidationError("حساب متعلق به شرکت دیگری است.")
            if not e.account.is_active:
                raise ValidationError(f"حساب {e.account.code} غیرفعال است.")

        self.is_posted = True
        self.posted_at = timezone.now()
        self.posted_by = user
        self.save(update_fields=["is_posted", "posted_at", "posted_by"])

    def delete(self, *args, **kwargs):
        if self.is_posted:
            raise ValidationError("سند ثبت‌شده قابل حذف نیست.")
        super().delete(*args, **kwargs)

class JournalEntry(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="entries")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_entries")
    debit = models.DecimalField("بدهکار", max_digits=20, decimal_places=2, default=Decimal("0"))
    credit = models.DecimalField("بستانکار", max_digits=20, decimal_places=2, default=Decimal("0"))
    description = models.CharField("شرح آرتیکل", max_length=500, blank=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "id"]
        verbose_name = "آرتیکل"
        verbose_name_plural = "آرتیکل‌ها"

    def __str__(self) -> str:
        if self.debit:
            return f"بد {self.account.code} = {self.debit}"
        return f"بس {self.account.code} = {self.credit}"

    @property
    def amount(self) -> Decimal:
        return self.debit or self.credit
