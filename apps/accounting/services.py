"""سرویس‌های ساخت سند و گزارش‌های مالی."""
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum

from apps.core.models import FiscalYear
from .models import Account, Journal, JournalEntry

def get_coa_account(company, key: str) -> Account:
    code = settings.COA[key]
    return Account.objects.get(company=company, code=code)

def create_sale_journal(*, company, fiscal_year, date, number, description,
                        customer_name, total_after_discount, total_vat, total_amount,
                        total_cogs=Decimal("0"), user=None):
    ar = get_coa_account(company, "AR")
    revenue = get_coa_account(company, "SALES_REVENUE")
    vat = get_coa_account(company, "VAT_PAYABLE")

    journal = Journal.objects.create(
        company=company, fiscal_year=fiscal_year, number=number, date=date,
        description=description, created_by=user,
    )
    seq = 1
    JournalEntry.objects.create(journal=journal, account=ar, debit=total_amount,
                                description=f"طلب از {customer_name}", sequence=seq); seq += 1
    JournalEntry.objects.create(journal=journal, account=revenue, credit=total_after_discount,
                                description="درآمد فروش", sequence=seq); seq += 1
    if total_vat:
        JournalEntry.objects.create(journal=journal, account=vat, credit=total_vat,
                                    description="مالیات بر ارزش افزوده", sequence=seq); seq += 1
    if total_cogs and total_cogs > 0:
        cogs = get_coa_account(company, "COGS")
        inv = get_coa_account(company, "INVENTORY")
        JournalEntry.objects.create(journal=journal, account=cogs, debit=total_cogs,
                                    description="بهای تمام شده کالای فروش رفته", sequence=seq); seq += 1
        JournalEntry.objects.create(journal=journal, account=inv, credit=total_cogs,
                                    description="کاهش موجودی کالا", sequence=seq); seq += 1
    return journal

def create_sale_return_journal(*, company, fiscal_year, date, number, description,
                               customer_name, total_after_discount, total_vat, total_amount,
                               total_cogs=Decimal("0"), user=None):
    ar = get_coa_account(company, "AR")
    revenue = get_coa_account(company, "SALES_REVENUE")
    vat = get_coa_account(company, "VAT_PAYABLE")

    journal = Journal.objects.create(
        company=company, fiscal_year=fiscal_year, number=number, date=date,
        description=description, created_by=user,
    )
    seq = 1
    JournalEntry.objects.create(journal=journal, account=ar, credit=total_amount,
                                description=f"کاهش طلب از {customer_name}", sequence=seq); seq += 1
    JournalEntry.objects.create(journal=journal, account=revenue, debit=total_after_discount,
                                description="برگشت از فروش", sequence=seq); seq += 1
    if total_vat:
        JournalEntry.objects.create(journal=journal, account=vat, debit=total_vat,
                                    description="برگشت مالیات بر ارزش افزوده", sequence=seq); seq += 1
    if total_cogs and total_cogs > 0:
        cogs = get_coa_account(company, "COGS")
        inv = get_coa_account(company, "INVENTORY")
        JournalEntry.objects.create(journal=journal, account=inv, debit=total_cogs,
                                    description="افزایش موجودی کالا (برگشتی)", sequence=seq); seq += 1
        JournalEntry.objects.create(journal=journal, account=cogs, credit=total_cogs,
                                    description="برگشت بهای تمام شده", sequence=seq); seq += 1
    return journal

def create_purchase_journal(*, company, fiscal_year, date, number, description,
                            supplier_name, total_after_discount, total_vat, total_amount,
                            user=None):
    ap = get_coa_account(company, "AP")
    inventory = get_coa_account(company, "INVENTORY")
    vat = get_coa_account(company, "VAT_PAYABLE")

    journal = Journal.objects.create(
        company=company, fiscal_year=fiscal_year, number=number, date=date,
        description=description, created_by=user,
    )
    seq = 1
    JournalEntry.objects.create(journal=journal, account=inventory, debit=total_after_discount,
                                description="خرید کالا", sequence=seq); seq += 1
    if total_vat:
        JournalEntry.objects.create(journal=journal, account=vat, debit=total_vat,
                                    description="مالیات بر ارزش افزوده خرید", sequence=seq); seq += 1
    JournalEntry.objects.create(journal=journal, account=ap, credit=total_amount,
                                description=f"بدهی به {supplier_name}", sequence=seq); seq += 1
    return journal

def create_purchase_return_journal(*, company, fiscal_year, date, number, description,
                                   supplier_name, total_after_discount, total_vat, total_amount,
                                   inventory_credit, user=None):
    ap = get_coa_account(company, "AP")
    inventory = get_coa_account(company, "INVENTORY")
    vat = get_coa_account(company, "VAT_PAYABLE")
    cogs = get_coa_account(company, "COGS")

    journal = Journal.objects.create(
        company=company, fiscal_year=fiscal_year, number=number, date=date,
        description=description, created_by=user,
    )
    seq = 1
    JournalEntry.objects.create(journal=journal, account=ap, debit=total_amount,
                                description=f"کاهش بدهی به {supplier_name}", sequence=seq); seq += 1
    JournalEntry.objects.create(journal=journal, account=inventory, credit=inventory_credit,
                                description="کاهش موجودی کالا (برگشتی)", sequence=seq); seq += 1
    if total_vat:
        JournalEntry.objects.create(journal=journal, account=vat, credit=total_vat,
                                    description="برگشت مالیات خرید", sequence=seq); seq += 1

    variance = inventory_credit - total_after_discount
    if variance > 0:
        JournalEntry.objects.create(journal=journal, account=cogs, debit=variance,
                                    description="واریانس بهای برگشت خرید", sequence=seq)
    elif variance < 0:
        JournalEntry.objects.create(journal=journal, account=cogs, credit=-variance,
                                    description="واریانس بهای برگشت خرید", sequence=seq)
    return journal

def trial_balance(fiscal_year: FiscalYear):
    rows = (
        JournalEntry.objects
        .filter(journal__fiscal_year=fiscal_year, journal__is_posted=True)
        .values("account__code", "account__name", "account__account_type")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )
    result = []
    total_debit = total_credit = Decimal("0")
    for r in rows:
        d = r["debit"] or Decimal("0")
        c = r["credit"] or Decimal("0")
        total_debit += d
        total_credit += c
        result.append({
            "code": r["account__code"], "name": r["account__name"],
            "type": r["account__account_type"],
            "debit": d, "credit": c, "balance": d - c,
        })
    return result, total_debit, total_credit

def ledger(fiscal_year: FiscalYear, account: Account):
    entries = (
        JournalEntry.objects
        .filter(journal__fiscal_year=fiscal_year, journal__is_posted=True, account=account)
        .select_related("journal")
        .order_by("journal__date", "journal_id", "sequence")
    )
    running = Decimal("0")
    rows = []
    sign = 1 if account.normal_balance == "debit" else -1
    for e in entries:
        delta = (e.debit - e.credit) * sign
        running += delta
        rows.append({
            "date": e.journal.date, "number": e.journal.number,
            "description": e.description or e.journal.description,
            "debit": e.debit, "credit": e.credit, "balance": running,
        })
    return rows, running
