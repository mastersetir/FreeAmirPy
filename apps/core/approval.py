"""فرآیند تأیید (Approval workflow)."""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "در انتظار تأیید"
    APPROVED = "approved", "تأیید شد"
    REJECTED = "rejected", "رد شد"

class ApprovalRequest(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, related_name="approval_requests")
    requested_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="approvals_requested")
    requested_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=300, blank=True)

    status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="approvals_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "درخواست تأیید"
        verbose_name_plural = "درخواست‌های تأیید"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} — {self.content_type.model} #{self.object_id} ({self.get_status_display()})"

    def approve(self, user, notes: str = ""):
        self.status = ApprovalStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

    def reject(self, user, notes: str = ""):
        self.status = ApprovalStatus.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

def has_approved(obj) -> bool:
    ct = ContentType.objects.get_for_model(obj.__class__)
    return ApprovalRequest.objects.filter(
        content_type=ct, object_id=obj.pk, status=ApprovalStatus.APPROVED,
    ).exists()

def get_pending(obj):
    ct = ContentType.objects.get_for_model(obj.__class__)
    return ApprovalRequest.objects.filter(
        content_type=ct, object_id=obj.pk, status=ApprovalStatus.PENDING,
    ).first()

def request_approval(obj, user, description: str = ""):
    ct = ContentType.objects.get_for_model(obj.__class__)
    existing = ApprovalRequest.objects.filter(
        content_type=ct, object_id=obj.pk, status=ApprovalStatus.PENDING,
    ).first()
    if existing:
        return existing
    return ApprovalRequest.objects.create(
        content_type=ct, object_id=obj.pk,
        company=obj.company, requested_by=user,
        description=description or str(obj)[:300],
    )
