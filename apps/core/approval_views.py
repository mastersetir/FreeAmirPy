"""ویوهای تأیید اسناد."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.core.activity import log_activity
from apps.core.utils import get_active_company

from .approval import (
    ApprovalRequest, ApprovalStatus, has_approved, request_approval,
)

class ApprovalListView(LoginRequiredMixin, ListView):
    model = ApprovalRequest
    template_name = "core/approval_list.html"
    context_object_name = "requests"
    paginate_by = 50

    def get_queryset(self):
        qs = ApprovalRequest.objects.select_related(
            "requested_by", "reviewed_by", "company", "content_type",
        ).order_by("-requested_at")
        company_id = self.request.session.get("company_id")
        if company_id:
            qs = qs.filter(company_id=company_id)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = ApprovalStatus.choices
        return ctx

class RequestApprovalView(LoginRequiredMixin, View):
    def post(self, request, model_name: str, pk: int):
        from apps.accounting.models import Journal
        from apps.purchases.models import PurchaseInvoice, PurchaseReturn
        from apps.sales.models import SaleInvoice, SaleReturn

        model_map = {
            "journal": Journal,
            "sale-invoice": SaleInvoice,
            "sale-return": SaleReturn,
            "purchase-invoice": PurchaseInvoice,
            "purchase-return": PurchaseReturn,
        }
        model = model_map.get(model_name)
        if not model:
            messages.error(request, "نوع سند نامعتبر است.")
            return redirect(reverse("core:approvals"))

        company = get_active_company(request)
        obj = get_object_or_404(model, pk=pk, company=company)
        if has_approved(obj):
            messages.info(request, "این سند قبلاً تأیید شده است.")
        else:
            request_approval(obj, request.user)
            log_activity(action="create", obj=obj, request=request, description="درخواست تأیید")
            messages.success(request, "درخواست تأیید ثبت شد.")
        return redirect(request.META.get("HTTP_REFERER") or reverse("core:approvals"))

class ReviewApprovalView(LoginRequiredMixin, View):
    def post(self, request, pk: int, action: str):
        req = get_object_or_404(ApprovalRequest, pk=pk)
        if request.user.role not in ("admin",) and not request.user.is_superuser:
            messages.error(request, "فقط مدیر می‌تواند تأیید/رد کند.")
            return redirect(reverse("core:approvals"))

        notes = request.POST.get("notes", "")
        if action == "approve":
            req.approve(request.user, notes)
            log_activity(action="approve", obj=req.content_object, request=request,
                         description=f"تأیید درخواست #{req.pk}")
            messages.success(request, "تأیید شد.")
        elif action == "reject":
            req.reject(request.user, notes)
            log_activity(action="reject", obj=req.content_object, request=request,
                         description=f"رد درخواست #{req.pk}")
            messages.warning(request, "رد شد.")
        return redirect(reverse("core:approvals"))
