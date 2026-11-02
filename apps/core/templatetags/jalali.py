"""فیلترهای قالب برای تبدیل تاریخ میلادی به جلالی و قالب‌بندی اعداد."""
import jdatetime
from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def to_jalali(value, fmt="%Y/%m/%d"):
    if not value:
        return ""
    if hasattr(value, "date"):
        value = value.date()
    return jdatetime.date.fromgregorian(date=value).strftime(fmt)

@register.filter
def to_jalali_dt(value, fmt="%Y/%m/%d %H:%M"):
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return jdatetime.datetime.fromgregorian(datetime=value).strftime(fmt)

@register.filter
def money(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return value
