from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.accounting.models import Journal
from apps.core.activity import ActivityLog
from apps.core.models import Company, FiscalYear
from apps.core.utils import get_active_company, get_active_fiscal_year

class DashboardView(LoginRequiredMixin, View):
    template_name = "dashboard.html"

    def get(self, request):
        company = get_active_company(request)
        fiscal_year = get_active_fiscal_year(request)

        stats = {"journals": 0, "posted": 0, "unposted": 0}
        recent_journals = []
        recent_activity = []
        if fiscal_year:
            qs = Journal.objects.filter(fiscal_year=fiscal_year)
            stats["journals"] = qs.count()
            stats["posted"] = qs.filter(is_posted=True).count()
            stats["unposted"] = qs.filter(is_posted=False).count()
            recent_journals = qs.order_by("-date", "-id")[:8]
        if company:
            recent_activity = (
                ActivityLog.objects.filter(company=company)
                .select_related("user").order_by("-created_at")[:10]
            )

        return render(request, self.template_name, {
            "stats": stats,
            "recent_journals": recent_journals,
            "recent_activity": recent_activity,
            "companies": Company.objects.filter(is_active=True),
            "fiscal_years": FiscalYear.objects.filter(company=company) if company else [],
        })

def _user_can_access_company(user, company) -> bool:
    if user.is_superuser:
        return True
    from apps.accounts.models import CompanyAccess
    return CompanyAccess.objects.filter(user=user, company=company).exists()

def switch_company(request, company_id):
    company = get_object_or_404(Company, pk=company_id, is_active=True)
    if not _user_can_access_company(request.user, company):
        messages.error(request, "دسترسی به این شرکت ندارید.")
        return redirect("core:dashboard")
    request.session["company_id"] = company_id
    request.session.pop("fiscal_year_id", None)
    return redirect(request.META.get("HTTP_REFERER", "/"))

def switch_fiscal_year(request, fy_id):
    fy = get_object_or_404(FiscalYear, pk=fy_id)
    if not _user_can_access_company(request.user, fy.company):
        messages.error(request, "دسترسی ندارید.")
        return redirect("core:dashboard")
    request.session["fiscal_year_id"] = fy_id
    return redirect(request.META.get("HTTP_REFERER", "/"))

class ActivityLogView(LoginRequiredMixin, ListView):
    model = ActivityLog
    template_name = "core/activity_log.html"
    context_object_name = "activities"
    paginate_by = 100

    def get_queryset(self):
        qs = ActivityLog.objects.select_related("user", "company").order_by("-created_at")
        action = self.request.GET.get("action")
        entity = self.request.GET.get("entity")
        company_id = self.request.session.get("company_id")
        if action:
            qs = qs.filter(action=action)
        if entity:
            qs = qs.filter(entity=entity)
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

    def get_context_data(self, **kwargs):
        from .activity import ActivityAction
        ctx = super().get_context_data(**kwargs)
        ctx["actions"] = ActivityAction.choices
        ctx["entities"] = (ActivityLog.objects.values_list("entity", flat=True)
                           .distinct().order_by("entity"))
        return ctx
