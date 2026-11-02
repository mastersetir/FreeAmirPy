"""بستن سال مالی: انتقال درآمدها و هزینه‌ها به سود انباشته."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.activity import log_activity
from .models import Account, Journal, JournalEntry

def preview_close(fiscal_year) -> dict:
    rows = (
        JournalEntry.objects
        .filter(journal__fiscal_year=fiscal_year, journal__is_posted=True)
        .filter(account__account_type__in=["REVENUE", "EXPENSE"])
        .values("account__code", "account__name", "account__account_type")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
    )
    revenues, expenses = [], []
    net = Decimal("0")
    for r in rows:
        d = r["debit"] or Decimal("0")
        c = r["credit"] or Decimal("0")
        if r["account__account_type"] == "REVENUE":
            bal = c - d
            if bal != 0:
                revenues.append({"code": r["account__code"], "name": r["account__name"], "balance": bal})
            net += bal
        else:
            bal = d - c
            if bal != 0:
                expenses.append({"code": r["account__code"], "name": r["account__name"], "balance": bal})
            net -= bal

    return {
        "revenues": revenues, "expenses": expenses, "net_income": net,
        "can_close": not Journal.objects.filter(fiscal_year=fiscal_year, is_posted=False).exists(),
    }

@transaction.atomic
def close_fiscal_year(fiscal_year, user=None, request=None):
    if fiscal_year.is_closed:
        raise ValidationError("این سال مالی قبلاً بسته شده است.")
    if Journal.objects.filter(fiscal_year=fiscal_year, is_posted=False).exists():
        raise ValidationError("قبل از بستن سال مالی، همه‌ی اسناد باید ثبت شوند.")

    data = preview_close(fiscal_year)
    retained_code = settings.COA.get("RETAINED_EARNINGS", "3102")
    retained = Account.objects.filter(company=fiscal_year.company, code=retained_code).first()
    if not retained:
        raise ValidationError(
            f"حساب سود انباشته (کد {retained_code}) وجود ندارد. init_coa را اجرا کنید."
        )

    if not data["revenues"] and not data["expenses"]:
        fiscal_year.is_closed = True
        fiscal_year.closed_at = timezone.now()
        fiscal_year.save(update_fields=["is_closed", "closed_at"])
        return None

    journal = Journal.objects.create(
        company=fiscal_year.company, fiscal_year=fiscal_year,
        number=f"CLOSE-{fiscal_year.name}", date=fiscal_year.end_date,
        description=f"بستن سال مالی {fiscal_year.name}", created_by=user,
    )

    seq = 1
    for r in data["revenues"]:
        acc = Account.objects.get(company=fiscal_year.company, code=r["code"])
        if r["balance"] > 0:
            JournalEntry.objects.create(journal=journal, account=acc, debit=r["balance"],
                                        description=f"بستن درآمد {r['name']}", sequence=seq)
        else:
            JournalEntry.objects.create(journal=journal, account=acc, credit=-r["balance"],
                                        description=f"بستن درآمد {r['name']}", sequence=seq)
        seq += 1

    for e in data["expenses"]:
        acc = Account.objects.get(company=fiscal_year.company, code=e["code"])
        if e["balance"] > 0:
            JournalEntry.objects.create(journal=journal, account=acc, credit=e["balance"],
                                        description=f"بستن هزینه {e['name']}", sequence=seq)
        else:
            JournalEntry.objects.create(journal=journal, account=acc, debit=-e["balance"],
                                        description=f"بستن هزینه {e['name']}", sequence=seq)
        seq += 1

    net = data["net_income"]
    if net > 0:
        JournalEntry.objects.create(journal=journal, account=retained, credit=net,
                                    description="سود خالص دوره به سود انباشته", sequence=seq)
    elif net < 0:
        JournalEntry.objects.create(journal=journal, account=retained, debit=-net,
                                    description="زیان خالص دوره به سود انباشته", sequence=seq)

    journal.post(user=user)

    fiscal_year.is_closed = True
    fiscal_year.closed_at = timezone.now()
    fiscal_year.closing_journal = journal
    fiscal_year.save(update_fields=["is_closed", "closed_at", "closing_journal"])

    log_activity(action="post", obj=journal, user=user, request=request,
                 description=f"بستن سال مالی {fiscal_year.name} — خالص: {net:,.2f}")
    return journal
