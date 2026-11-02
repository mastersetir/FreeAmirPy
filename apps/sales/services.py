"""سرویس‌های فروش: ثبت فاکتور و برگشت + انبار + سند + لاگ."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.accounting.services import create_sale_journal, create_sale_return_journal
from apps.core.activity import log_activity
from apps.inventory.services import get_or_create_default_warehouse, issue_stock, receive_stock

from .models import SaleInvoice, SaleReturn

@transaction.atomic
def post_sale_invoice(invoice: SaleInvoice, user=None, request=None):
    if invoice.status != SaleInvoice.Status.DRAFT:
        raise ValidationError("این فاکتور قبلاً ثبت شده است.")

    cogs = Decimal("0")
    default_wh = None
    for line in invoice.lines.select_related("product", "warehouse"):
        wh = line.warehouse or default_wh
        if not wh:
            wh = get_or_create_default_warehouse(invoice.company)
            default_wh = wh
        if wh.company_id != invoice.company_id:
            raise ValidationError(f"انبار «{wh.name}» متعلق به شرکت دیگری است.")
        move = issue_stock(
            warehouse=wh, product=line.product, qty=line.quantity,
            date=invoice.date, reference=f"INV-{invoice.number}",
        )
        cogs += move.total_cost
        line.unit_cogs = move.unit_cost
        line.save(update_fields=["unit_cogs"])

    journal = create_sale_journal(
        company=invoice.company, fiscal_year=invoice.fiscal_year,
        date=invoice.date, number=f"S-{invoice.number}",
        description=f"فروش به {invoice.customer.name}",
        customer_name=invoice.customer.name,
        total_after_discount=invoice.total_after_discount,
        total_vat=invoice.total_vat,
        total_amount=invoice.total_amount,
        total_cogs=cogs,
        user=user,
    )
    journal.post(user=user)

    invoice.journal = journal
    invoice.status = SaleInvoice.Status.POSTED
    invoice.save(update_fields=["journal", "status"])

    log_activity(
        action="post", obj=invoice, user=user, request=request,
        changes={"status": "posted", "journal": journal.number},
        description=f"بهای تمام شده: {cogs:,.2f}",
    )
    return journal, cogs

@transaction.atomic
def post_sale_return(return_doc: SaleReturn, user=None, request=None):
    if return_doc.status != SaleReturn.Status.DRAFT:
        raise ValidationError("این برگشت قبلاً ثبت شده است.")
    if return_doc.invoice.status != SaleInvoice.Status.POSTED:
        raise ValidationError("فاکتور اصلی باید ثبت‌شده باشد.")

    total_cogs = Decimal("0")
    for line in return_doc.lines.select_related("original_line", "product"):
        orig = line.original_line
        if line.quantity <= 0:
            continue
        if line.quantity > line.max_returnable():
            raise ValidationError(
                f"مقدار برگشتی برای «{line.product.name}» بیش از حد مجاز است "
                f"(حداکثر {line.max_returnable()})."
            )
        wh = orig.warehouse
        if not wh:
            wh = get_or_create_default_warehouse(return_doc.company)
        if wh.company_id != return_doc.company_id:
            raise ValidationError(f"انبار «{wh.name}» متعلق به شرکت دیگری است.")
        move = receive_stock(
            warehouse=wh, product=line.product, qty=line.quantity,
            unit_cost=orig.unit_cogs, date=return_doc.date,
            reference=f"SRET-{return_doc.number}",
        )
        total_cogs += move.total_cost

    journal = create_sale_return_journal(
        company=return_doc.company, fiscal_year=return_doc.fiscal_year,
        date=return_doc.date, number=f"SR-{return_doc.number}",
        description=f"برگشت از فروش {return_doc.invoice.number} — {return_doc.invoice.customer.name}",
        customer_name=return_doc.invoice.customer.name,
        total_after_discount=return_doc.total_after_discount,
        total_vat=return_doc.total_vat,
        total_amount=return_doc.total_amount,
        total_cogs=total_cogs,
        user=user,
    )
    journal.post(user=user)

    return_doc.journal = journal
    return_doc.status = SaleReturn.Status.POSTED
    return_doc.save(update_fields=["journal", "status"])

    log_activity(
        action="post", obj=return_doc, user=user, request=request,
        changes={"status": "posted", "journal": journal.number},
        description=f"برگشت COGS: {total_cogs:,.2f}",
    )
    return journal, total_cogs

def build_sale_return_lines(return_doc: SaleReturn):
    from .models import SaleReturnLine
    return_doc.lines.all().delete()
    seq = 1
    for line in return_doc.invoice.lines.select_related("product"):
        max_q = line.quantity - (
            line.return_lines.filter(return_doc__status=SaleReturn.Status.POSTED)
            .exclude(return_doc=return_doc).aggregate(s=Sum("quantity"))["s"] or Decimal("0")
        )
        if max_q <= 0:
            continue
        SaleReturnLine.objects.create(
            return_doc=return_doc, original_line=line, product=line.product,
            quantity=max_q, unit_price=line.unit_price,
            discount=line.discount, vat_rate=line.vat_rate,
            unit_cogs=line.unit_cogs, sequence=seq,
        )
        seq += 1
    return_doc.recalc_totals
