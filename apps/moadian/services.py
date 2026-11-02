"""سرویس ارسال هر ۴ نوع سند به مودیان + استعلام."""
import logging

from django.utils import timezone as dj_timezone

from apps.core.activity import log_activity
from .client import (
    MoadianClient, MoadianError,
    build_invoice_body, build_invoice_header,
)
from .models import MoadianConfig, MoadianInvoice

logger = logging.getLogger("apps.moadian")


def get_config(company) -> MoadianConfig:
    try:
        return MoadianConfig.objects.get(company=company, is_active=True)
    except MoadianConfig.DoesNotExist:
        raise MoadianError(f"تنظیمات مودیان برای شرکت «{company.name}» پیدا نشد.")


def _send_document(document, document_type: str, user=None, request=None) -> MoadianInvoice:
    """ارسال یک سند (هر ۴ نوع) به مودیان."""
    from apps.sales.models import SaleInvoice, SaleReturn
    from apps.purchases.models import PurchaseInvoice, PurchaseReturn

    if isinstance(document, SaleInvoice) and document.status == SaleInvoice.Status.DRAFT:
        raise MoadianError("ابتدا فاکتور را ثبت کنید (سند حسابداری ایجاد شود).")
    if isinstance(document, SaleReturn) and document.status == SaleReturn.Status.DRAFT:
        raise MoadianError("ابتدا برگشت را ثبت کنید.")
    if isinstance(document, PurchaseInvoice) and document.status == PurchaseInvoice.Status.DRAFT:
        raise MoadianError("ابتدا فاکتور خرید را ثبت کنید.")
    if isinstance(document, PurchaseReturn) and document.status == PurchaseReturn.Status.DRAFT:
        raise MoadianError("ابتدا برگشت خرید را ثبت کنید.")

    config = get_config(document.company)
    client = MoadianClient(config)

    record = MoadianInvoice.objects.create(
        company=document.company,
        document_type=document_type,
        document_id=document.pk,
        document_repr=str(document)[:200],
        status=MoadianInvoice.Status.PENDING,
    )

    try:
        header = build_invoice_header(config=config, document=document, document_type=document_type)
        body = build_invoice_body(document, document_type)
        packet = client.build_packet(header, body)
        record.request_payload = packet
        record.save(update_fields=["request_payload"])

        results = client.send_invoices([packet])
        result = results[0] if results else {}
        record.response_payload = result
        record.reference_number = str(result.get("referenceNumber") or result.get("reference_number") or "")
        record.tax_id = str(result.get("taxId") or result.get("taxID") or "")

        code = str(result.get("code") or result.get("status") or "")
        if code in ("200", "success", "OK"):
            record.status = MoadianInvoice.Status.SENT
            record.sent_at = dj_timezone.now()
        else:
            record.status = MoadianInvoice.Status.FAILED
            record.error_message = str(result.get("message") or result.get("error") or result)
        record.save()

        log_activity(
            action="send", obj=document, user=user, request=request,
            description=f"مودیان: {record.get_status_display()} — ref={record.reference_number}",
        )
        return record
    except MoadianError as exc:
        record.status = MoadianInvoice.Status.FAILED
        record.error_message = str(exc)
        record.save()
        raise
    except Exception as exc:  # noqa: BLE001
        record.status = MoadianInvoice.Status.FAILED
        record.error_message = f"خطای پیش‌بینی‌نشده: {exc}"
        record.save()
        raise MoadianError(str(exc)) from exc


def send_sale_invoice(document, user=None, request=None) -> MoadianInvoice:
    return _send_document(document, MoadianInvoice.DocumentType.SALE_INVOICE, user, request)


def send_sale_return(document, user=None, request=None) -> MoadianInvoice:
    return _send_document(document, MoadianInvoice.DocumentType.SALE_RETURN, user, request)


def send_purchase_invoice(document, user=None, request=None) -> MoadianInvoice:
    return _send_document(document, MoadianInvoice.DocumentType.PURCHASE_INVOICE, user, request)


def send_purchase_return(document, user=None, request=None) -> MoadianInvoice:
    return _send_document(document, MoadianInvoice.DocumentType.PURCHASE_RETURN, user, request)


def refresh_status(record: MoadianInvoice) -> MoadianInvoice:
    if not record.reference_number:
        raise MoadianError("این رکورد شماره مرجع ندارد.")
    config = get_config(record.company)
    client = MoadianClient(config)
    results = client.inquiry_by_references([record.reference_number])
    result = results[0] if results else {}
    record.response_payload = result
    code = str(result.get("code") or result.get("status") or "")
    if code in ("200", "success", "OK"):
        record.status = MoadianInvoice.Status.SUCCESS
        record.verified_at = dj_timezone.now()
        if not record.tax_id:
            record.tax_id = str(result.get("taxId") or result.get("taxID") or "")
    elif code:
        record.status = MoadianInvoice.Status.REJECTED
        record.error_message = str(result.get("message") or "")
    record.save()
    return record


def validate_economic_code(company, economic_code: str) -> dict:
    config = get_config(company)
    client = MoadianClient(config)
    return client.get_economic_code_info(economic_code)