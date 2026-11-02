"""کلاینت کامل API سامانه مودیان (نسخه ۲)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone as dj_timezone

from .crypto import canonical_json, sign_packet
from .models import MoadianConfig, MoadianLog

logger = logging.getLogger("apps.moadian")

class MoadianError(Exception):
    """خطای سامانه مودیان."""

class MoadianClient:
    BASE_PATHS = {
        "token": "/requestsmanager/api/v2/oauth2/token",
        "server_info": "/requestsmanager/api/v2/server-information",
        "fiscal_info": "/requestsmanager/api/v2/fiscal-information",
        "economic_codes": "/requestsmanager/api/v2/economic-codes",
        "invoices": "/requestsmanager/api/v2/invoices",
        "invoices_result": "/requestsmanager/api/v2/invoices/result",
        "invoice_detail": "/requestsmanager/api/v2/invoices/{ref}",
        "inquiry_refs": "/requestsmanager/api/v2/inquiry-by-reference-numbers",
        "inquiry_uids": "/requestsmanager/api/v2/inquiry-by-uid-list",
        "inquiry_time": "/requestsmanager/api/v2/inquiry-by-time",
    }

    def __init__(self, config: MoadianConfig, timeout: int = 30):
        self.config = config
        self.timeout = timeout
        self.base_url = (
            settings.MOADIAN_PRODUCTION_BASE_URL
            if config.environment == MoadianConfig.Environment.PRODUCTION
            else settings.MOADIAN_SANDBOX_BASE_URL
        )

    def _token_is_valid(self) -> bool:
        if not self.config.cached_token or not self.config.token_expires_at:
            return False
        return self.config.token_expires_at > dj_timezone.now() + timedelta(seconds=30)

    def get_token(self, force: bool = False) -> str:
        if not force and self._token_is_valid():
            return self.config.cached_token
        url = self.base_url + self.BASE_PATHS["token"]
        payload = {"client_id": self.config.client_id, "client_secret": self.config.client_secret}
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise MoadianError(f"خطای شبکه در دریافت توکن: {exc}") from exc
        self._log("token", "POST", canonical_json(payload), resp)
        if resp.status_code != 200:
            raise MoadianError(f"خطا در دریافت توکن ({resp.status_code}): {resp.text}")
        data = resp.json()
        token = data.get("token") or data.get("access_token")
        if not token:
            raise MoadianError(f"پاسخ نامعتبر توکن: {data}")
        expires_in = int(data.get("expires_in", 3600))
        self.config.cached_token = token
        self.config.token_expires_at = dj_timezone.now() + timedelta(seconds=expires_in)
        self.config.save(update_fields=["cached_token", "token_expires_at"])
        return token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.get_token()}", "Content-Type": "application/json"}

    def _get(self, key: str) -> dict:
        url = self.base_url + self.BASE_PATHS[key]
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise MoadianError(f"خطای شبکه ({key}): {exc}") from exc
        self._log(key, "GET", "", resp)
        if resp.status_code != 200:
            raise MoadianError(f"خطای {key} ({resp.status_code}): {resp.text}")
        return resp.json()

    def _post(self, key: str, payload: dict) -> Any:
        url = self.base_url + self.BASE_PATHS[key]
        body = canonical_json(payload)
        try:
            resp = requests.post(url, data=body, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise MoadianError(f"خطای شبکه ({key}): {exc}") from exc
        self._log(key, "POST", body, resp)
        if resp.status_code not in (200, 201):
            raise MoadianError(f"خطای {key} ({resp.status_code}): {resp.text}")
        return resp.json()

    def get_server_info(self) -> dict:
        return self._get("server_info")

    def get_fiscal_info(self) -> dict:
        return self._get("fiscal_info")

    def get_economic_code_info(self, economic_code: str) -> dict:
        return self._post("economic_codes", {"economicCode": economic_code})

    def inquiry_by_references(self, references: list[str]) -> list[dict]:
        data = self._post("inquiry_refs", {"referenceNumbers": references})
        return data.get("result", data if isinstance(data, list) else [data])

    def inquiry_by_uids(self, uids: list[str]) -> list[dict]:
        data = self._post("inquiry_uids", {"uidList": uids})
        return data.get("result", data if isinstance(data, list) else [data])

    def inquiry_by_time(self, from_iso: str, to_iso: str) -> list[dict]:
        data = self._post("inquiry_time", {"startDate": from_iso, "endDate": to_iso})
        return data.get("result", data if isinstance(data, list) else [data])

    def get_invoice(self, reference_number: str) -> dict:
        url = self.base_url + self.BASE_PATHS["invoice_detail"].format(ref=reference_number)
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise MoadianError(f"خطای شبکه: {exc}") from exc
        self._log("invoice_detail", "GET", "", resp)
        if resp.status_code != 200:
            raise MoadianError(f"خطای دریافت ({resp.status_code}): {resp.text}")
        return resp.json()

    def build_packet(self, header: dict, body: list[dict]) -> dict:
        invoice = {"header": header, "body": body}
        signature_b64 = sign_packet(invoice, self.config.private_key)
        return {"header": header, "payload": signature_b64}

    def send_invoices(self, packets: list[dict]) -> list[dict]:
        data = self._post("invoices", {"packets": packets})
        return data.get("result", data if isinstance(data, list) else [data])

    def get_send_result(self, reference_numbers: list[str]) -> list[dict]:
        data = self._post("invoices_result", {"referenceNumbers": reference_numbers})
        return data.get("result", data if isinstance(data, list) else [data])

    def _log(self, endpoint_key: str, method: str, req_body: str, resp: requests.Response):
        MoadianLog.objects.create(
            config=self.config,
            endpoint=self.base_url + self.BASE_PATHS.get(endpoint_key, endpoint_key),
            method=method,
            request_body=req_body[:20000],
            response_status=resp.status_code,
            response_body=resp.text[:20000],
        )
        logger.info("[moadian] %s %s → %s", method, endpoint_key, resp.status_code)

INTY_NORMAL = 1
INTY_CORRECTIVE = 2
INTY_RETURN = 3
INTY_REVOKE = 4

INP_NORMAL = 1
INP_SIMPLE = 2

INS_SALE = 1
INS_PURCHASE = 2
INS_SALE_RETURN = 3
INS_PURCHASE_RETURN = 4

TOB_NATURAL = 1
TOB_LEGAL = 2

def _to_epoch_ms(d) -> int:
    dt = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def _person_type(entity) -> int:
    if getattr(entity, "registration_number", None) or getattr(entity, "economic_code", None):
        return TOB_LEGAL
    return TOB_NATURAL

def build_invoice_header(*, config: MoadianConfig, document, document_type: str) -> dict:
    if document_type in ("sale_invoice", "sale_return"):
        invoice = document if document_type == "sale_invoice" else document.invoice
        customer = invoice.customer
        seller, buyer = document.company, customer
        inty = INTY_NORMAL if document_type == "sale_invoice" else INTY_RETURN
        ins = INS_SALE if document_type == "sale_invoice" else INS_SALE_RETURN
        irtaxid = "" if document_type == "sale_invoice" else _get_irtaxid(invoice, "sale_invoice")
    else:
        invoice = document if document_type == "purchase_invoice" else document.invoice
        supplier = invoice.supplier
        seller, buyer = supplier, document.company
        inty = INTY_NORMAL if document_type == "purchase_invoice" else INTY_RETURN
        ins = INS_PURCHASE if document_type == "purchase_invoice" else INS_PURCHASE_RETURN
        irtaxid = "" if document_type == "purchase_invoice" else _get_irtaxid(invoice, "purchase_invoice")

    ts = _to_epoch_ms(document.date)
    return {
        "taxID": config.tax_id,
        "indatim": ts,
        "indati2m": ts,
        "inno": document.number,
        "inty": inty,
        "inp": INP_NORMAL,
        "ins": ins,
        "tins": (seller.national_id or "")[:11],
        "tob": _person_type(seller),
        "bid": (buyer.national_id or "")[:11],
        "tinb": (buyer.economic_code or "")[:20],
        "bpc": (getattr(buyer, "postal_code", "") or "")[:10],
        "irtaxid": irtaxid,
        "tprdis": float(document.total_before_discount),
        "tdis": float(document.total_discount),
        "tadis": float(document.total_after_discount),
        "tvam": float(document.total_vat),
        "todam": 0.0,
        "tbill": float(document.total_amount),
        "setm": int(getattr(invoice, "settlement_method", 1)),
        "cap": "",
        "insp": (seller.economic_code or "")[:20],
        "tvop": 0.0,
        "tax17": 0.0,
    }

def build_invoice_body(document, document_type: str) -> list[dict]:
    body = []
    for line in document.lines.select_related("product"):
        body.append({
            "sstid": line.product.code,
            "sstt": line.product.name,
            "mu": line.product.unit or "عدد",
            "am": float(line.quantity),
            "fee": float(line.unit_price),
            "prdis": float(line.before_discount),
            "dis": float(line.discount),
            "adis": float(line.after_discount),
            "vra": int(line.vat_rate),
            "vam": float(line.vat_amount),
            "tsstam": float(line.total),
        })
    return body

def _get_irtaxid(original_document, document_type: str) -> str:
    from .models import MoadianInvoice
    record = (
        MoadianInvoice.objects
        .filter(document_type=document_type, document_id=original_document.pk)
        .exclude(tax_id="")
        .order_by("-id")
        .first()
    )
    return record.tax_id if record else ""
