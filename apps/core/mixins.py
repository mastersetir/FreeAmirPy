"""مدل‌های پایه‌ای برای مدل‌هایی که به شرکت/سال مالی وابسته‌اند."""
from django.core.exceptions import ValidationError
from django.db import models

class CompanyScopedModel(models.Model):
    """مدل پایه‌ای که همیشه به یک شرکت وابسته است."""
    company = models.ForeignKey("core.Company", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class FiscalYearScopedModel(CompanyScopedModel):
    """مدل پایه‌ای که وابسته به سال مالی است و پس از بستن، قفل می‌شود."""
    fiscal_year = models.ForeignKey("core.FiscalYear", on_delete=models.PROTECT, related_name="+")

    class Meta:
        abstract = True

    def _ensure_fiscal_year_open(self):
        if self.fiscal_year_id and self.fiscal_year.is_closed:
            raise ValidationError("سال مالی بسته شده است و اجازه‌ی تغییر وجود ندارد.")
