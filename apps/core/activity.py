"""لاگ فعالیت — ثبت تمام عملیات حساس سیستم."""
from django.db import models

class ActivityAction(models.TextChoices):
    CREATE = "create", "ایجاد"
    UPDATE = "update", "ویرایش"
    DELETE = "delete", "حذف"
    POST = "post", "ثبت"
    SEND = "send", "ارسال"
    APPROVE = "approve", "تأیید"
    REJECT = "reject", "رد"
    LOGIN = "login", "ورود"
    LOGOUT = "logout", "خروج"

class ActivityLog(models.Model):
    user = models.ForeignKey("accounts.User", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="activities")
    company = models.ForeignKey("core.Company", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="activities")
    action = models.CharField(max_length=20, choices=ActivityAction.choices)
    entity = models.CharField("موجودیت", max_length=100, db_index=True)
    entity_id = models.CharField("شناسه", max_length=50, blank=True)
    entity_repr = models.CharField("توضیح", max_length=300, blank=True)
    description = models.CharField("شرح عملیات", max_length=300, blank=True)
    changes = models.JSONField("تغییرات", default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "فعالیت"
        verbose_name_plural = "لاگ فعالیت‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["entity", "entity_id"]),
        ]

    def __str__(self) -> str:
        who = self.user.username if self.user else "سیستم"
        return f"{who} — {self.get_action_display()} {self.entity_repr}"

def _get_client_ip(request):
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def log_activity(*, action: str, obj, user=None, request=None,
                 changes: dict | None = None, description: str = ""):
    if request is not None and getattr(request, "user", None) and request.user.is_authenticated:
        user = request.user

    ActivityLog.objects.create(
        user=user if (user and getattr(user, "is_authenticated", False)) else None,
        company=getattr(obj, "company", None),
        action=action,
        entity=obj.__class__.__name__,
        entity_id=str(getattr(obj, "pk", "")) or "",
        entity_repr=str(obj)[:300],
        description=description[:300] if description else "",
        changes=changes or {},
        ip_address=_get_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:500] if request else ""),
    )
