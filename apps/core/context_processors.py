from django.conf import settings

from apps.core.utils import get_active_company, get_active_fiscal_year

def active_context(request):
    base = {"DEBUG": settings.DEBUG}
    if not request.user.is_authenticated:
        return base
    return {
        **base,
        "active_company": get_active_company(request),
        "active_fiscal_year": get_active_fiscal_year(request),
    }
