"""ابزارهای انتخاب شرکت/سال مالی فعال."""
from apps.core.models import Company, FiscalYear

def get_active_company(request):
    cid = request.session.get("company_id")
    if cid:
        try:
            return Company.objects.get(pk=cid, is_active=True)
        except Company.DoesNotExist:
            pass
    company = Company.objects.filter(is_active=True).first()
    if company:
        request.session["company_id"] = company.pk
    return company

def get_active_fiscal_year(request):
    fy_id = request.session.get("fiscal_year_id")
    company = get_active_company(request)
    if not company:
        return None
    if fy_id:
        try:
            return FiscalYear.objects.get(pk=fy_id, company=company)
        except FiscalYear.DoesNotExist:
            pass
    fy = FiscalYear.objects.filter(company=company, is_closed=False).order_by("-start_date").first()
    if fy:
        request.session["fiscal_year_id"] = fy.pk
    return fy
