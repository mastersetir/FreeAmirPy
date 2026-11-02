"""سرویس‌های خرید: ثبت فاکتور و برگشت + لاگ."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.accounting.services import create_purchase_journal, create_purchase_return_journal
from apps.core.activity import log_activity
from apps.inventory.services import get_or_create_default_warehouse, issue_stock, receive_stock

from .models import PurchaseInvoice, PurchaseReturn, PurchaseReturnLine


@transaction.atomic
def post_purchase_invoice(invoice: PurchaseInvoice, user=None, request=None):
    if invoice.status != PurchaseInvoice.Status.DRAFT:
        raise ValidationError("این فاکتور قبلاً ثبت شده است.")

    for line in invoice.lines.select_related("product", "warehouse"):
        wh = line.warehouse
        if not wh:
            wh = get_or_create_default_warehouse(invoice.company)
        if wh.company_id != invoice.company_id:
            raise ValidationError(f"انبار «{wh.name}» متعلق به شرکت دیگری است.")
        unit_cost = (
            (line.after_discount / line.quantity).quantize(Decimal("0.0001"))
            if line.quantity else Decimal("0")
        )
        receive_stock(
            warehouse=wh, product=line.product, qty=line.quantity,
            unit_cost=unit_cost, date=invoice.date,
            reference=f"PUR-{invoice.number}",
        )
        line.unit_cost = unit_cost
        line.save(update_fields=["unit_cost"])

    journal = create_purchase_journal(
        company=invoice.company, fiscal_year=invoice.fiscal_year,
        date=invoice.date, number=f"P-{invoice.number}",
        description=f"خرید از {invoice.supplier.name}",
        supplier_name=invoice.supplier.name,
        total_after_discount=invoice.total_after_discount,
        total_vat=invoice.total_vat,
        total_amount=invoice.total_amount,
        user=user,
    )
    journal.post(user=user)

    invoice.journal = journal
    invoice.status = PurchaseInvoice.Status.POSTED
    invoice.save(update_fields=["journal", "status"])

    log_activity(
        action="post", obj=invoice, user=user, request=request,
        changes={"status": "posted", "journal": journal.number},
        description=f"جمع فاکتور: {invoice.total_amount:,.2f}",
    )
    return journal


@transaction.atomic
def post_purchase_return(return_doc: PurchaseReturn, user=None, request=None):
    if return_doc.status != PurchaseReturn.Status.DRAFT:
        raise ValidationError("این برگشت قبلاً ثبت شده است.")
    if return_doc.invoice.status != PurchaseInvoice.Status.POSTED:
        raise ValidationError("فاکتور خرید اصلی باید ثبت‌شده باشد.")

    inventory_credit = Decimal("0")
    for line in return_doc.lines.select_related("original_line", "product"):
        if line.quantity <= 0:
            continue
        if line.quantity > line.max_returnable():
            raise ValidationError(
                f"مقدار برگشتی برای «{line.product.name}» بیش از حد مجاز است "
                f"(حداکثر {line.max_returnable()})."
            )
        wh = line.original_line.warehouse
        if not wh:
            wh = get_or_create_default_warehouse(return_doc.company)
        if wh.company_id != return_doc.company_id:
            raise ValidationError(f"انبار «{wh.name}» متعلق به شرکت دیگری است.")
        move = issue_stock(
            warehouse=wh, product=line.product, qty=line.quantity,
            date=return_doc.date, reference=f"PRET-{return_doc.number}",
        )
        inventory_credit += move.total_cost

    journal = create_purchase_return_journal(
        company=return_doc.company, fiscal_year=return_doc.fiscal_year,
        date=return_doc.date, number=f"PR-{return_doc.number}",
        description=f"برگشت به {return_doc.invoice.supplier.name} — فاکتور {return_doc.invoice.number}",
        supplier_name=return_doc.invoice.supplier.name,
        total_after_discount=return_doc.total_after_discount,
        total_vat=return_doc.total_vat,
        total_amount=return_doc.total_amount,
        inventory_credit=inventory_credit,
        user=user,
    )
    journal.post(user=user)

    return_doc.journal = journal
    return_doc.status = PurchaseReturn.Status.POSTED
    return_doc.save(update_fields=["journal", "status"])

    log_activity(
        action="post", obj=return_doc, user=user, request=request,
        changes={"status": "posted", "journal": journal.number},
        description=f"کاهش موجودی: {inventory_credit:,.2f}",
    )
    return journal, inventory_credit


def build_purchase_return_lines(return_doc: PurchaseReturn):
    return_doc.lines.all().delete()
    seq = 1
    for line in return_doc.invoice.lines.select_related("product"):
        max_q = line.quantity - (
            line.return_lines.filter(return_doc__status=PurchaseReturn.Status.POSTED)
            .exclude(return_doc=return_doc).aggregate(s=Sum("quantity"))["s"] or Decimal("0")
        )
        if max_q <= 0:
            continue
        PurchaseReturnLine.objects.create(
            return_doc=return_doc, original_line=line, product=line.product,
            quantity=max_q, unit_price=line.unit_price,
            discount=line.discount, vat_rate=line.vat_rate, sequence=seq,
        )
        seq += 1
    return_doc.recalc_totals()