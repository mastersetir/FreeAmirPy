"""کاربر سفارشی، نقش‌ها و دسترسی به شرکت‌ها."""
from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    ADMIN = "admin", "مدیر کل"
    ACCOUNTANT = "accountant", "حسابدار"
    SELLER = "seller", "فروشنده"
    WAREHOUSE = "warehouse", "انباردار"

class User(AbstractUser):
    role = models.CharField("نقش اصلی", max_length=20, choices=Role.choices, default=Role.ACCOUNTANT)
    phone = models.CharField("تلفن", max_length=30, blank=True)

    def can_post_journals(self) -> bool:
        return self.role in (Role.ADMIN, Role.ACCOUNTANT) or self.is_superuser

    def can_manage_accounts(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

class CompanyAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="company_access")
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, related_name="access_list")
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "company")]
        verbose_name = "دسترسی شرکت"
        verbose_name_plural = "دسترسی‌های شرکت"

    def __str__(self) -> str:
        return f"{self.user.username} → {self.company.name} ({self.get_role_display()})"
