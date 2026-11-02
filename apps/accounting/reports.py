"""گزارش‌های مالی: ترازنامه و صورت سود و زیان."""
from decimal import Decimal

from django.db.models import Sum

from .models import JournalEntry

def _net_by_account(company, date_from=None, date_to=None):
    qs = JournalEntry.objects.filter(journal__company=company, journal__is_posted=True)
    if date_from:
        qs = qs.filter(journal__date__gte=date_from)
    if date_to:
        qs = qs.filter(journal__date__lte=date_to)
    return qs.values("account__code", "account__name", "account__account_type").annotate(
        debit=Sum("debit"), credit=Sum("credit"),
    )

def _natural_balance(account_type: str, debit: Decimal, credit: Decimal) -> Decimal:
    if account_type in ("ASSET", "EXPENSE"):
        return debit - credit
    return credit - debit

def balance_sheet(company, as_of_date):
    rows = _net_by_account(company, date_to=as_of_date)
    sections = {"ASSET": [], "LIABILITY": [], "EQUITY": []}
    totals = {"ASSET": Decimal("0"), "LIABILITY": Decimal("0"), "EQUITY": Decimal("0")}
    revenue_total = expense_total = Decimal("0")

    for r in rows:
        debit = r["debit"] or Decimal("0")
        credit = r["credit"] or Decimal("0")
        atype = r["account__account_type"]
        net = _natural_balance(atype, debit, credit)
        if atype == "REVENUE":
            revenue_total += net
        elif atype == "EXPENSE":
            expense_total += net
        else:
            if net == 0:
                continue
            sections[atype].append({"code": r["account__code"], "name": r["account__name"], "balance": net})
            totals[atype] += net

    net_income = revenue_total - expense_total
    if net_income != 0:
        sections["EQUITY"].append({"code": "—", "name": "سود (زیان) انباشته دوره", "balance": net_income})
        totals["EQUITY"] += net_income

    total_liab_eq = totals["LIABILITY"] + totals["EQUITY"]
    return {
        "as_of_date": as_of_date,
        "assets": sections["ASSET"], "liabilities": sections["LIABILITY"], "equity": sections["EQUITY"],
        "total_assets": totals["ASSET"], "total_liabilities": totals["LIABILITY"],
        "total_equity": totals["EQUITY"], "total_liabilities_equity": total_liab_eq,
        "balanced": totals["ASSET"] == total_liab_eq,
    }

def income_statement(fiscal_year):
    rows = _net_by_account(fiscal_year.company, fiscal_year.start_date, fiscal_year.end_date)
    revenues, expenses = [], []
    total_revenue = total_expense = Decimal("0")
    for r in rows:
        debit = r["debit"] or Decimal("0")
        credit = r["credit"] or Decimal("0")
        atype = r["account__account_type"]
        net = _natural_balance(atype, debit, credit)
        if net == 0:
            continue
        row = {"code": r["account__code"], "name": r["account__name"], "amount": net}
        if atype == "REVENUE":
            revenues.append(row); total_revenue += net
        elif atype == "EXPENSE":
            expenses.append(row); total_expense += net
    return {
        "fiscal_year": fiscal_year, "revenues": revenues, "expenses": expenses,
        "total_revenue": total_revenue, "total_expense": total_expense,
        "net_income": total_revenue - total_expense,
    }
