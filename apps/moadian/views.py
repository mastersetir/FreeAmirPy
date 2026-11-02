from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.utils import get_active_company
from apps.purchases.models import PurchaseInvoice, PurchaseReturn
from apps.sales.models import SaleInvoice, SaleReturn

from .client import MoadianClient, MoadianError
from .forms import EconomicCodeInquiryForm, MoadianConfigForm
from .models import MoadianConfig, MoadianInvoice
from .services import (
    get_config, refresh_status, send_purchase_invoice, send_purchase_return,
    send_sale_invoice, send_sale_return, validate_economic_code,
)

class ScopedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.company = get_active_company(request)
        if not self.company:
            messages.error(request, "ابتدا یک شرکت فعال انتخاب کنید.")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

class ConfigView(ScopedMixin, View):
    template_name = "moadian/config.html"

    def get(self, request):
        config = MoadianConfig.objects.filter(company=self.company).first()
        return render(request, self.template_name, {"form": MoadianConfigForm(instance=config), "config": config})

    def post(self, request):
        config = MoadianConfig.objects.filter(company=self.company).first()
        form = MoadianConfigForm(request.POST, instance=config)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.company = self.company
            obj.save()
            messages.success(request, "تنظیمات مودیان ذخیره شد.")
            return redirect("moadian:config")
        return render(request, self.template_name, {"form": form, "config": config})

class InvoiceListView(ScopedMixin, ListView):
    model = MoadianInvoice
    template_name = "moadian/invoice_list.html"
    context_object_name = "records"
    paginate_by = 50

    def get_queryset(self):
        qs = MoadianInvoice.objects.filter(company=self.company).order_by("-id")
        dt = self.request.GET.get("document_type")
        if dt:
            qs = qs.filter(document_type=dt)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["document_types"] = MoadianInvoice.DocumentType.choices
        return ctx

class SendView(ScopedMixin, View):
    def post(self, request, document_type, pk):
        dispatch = {
            MoadianInvoice.DocumentType.SALE_INVOICE: (SaleInvoice, send_sale_invoice, "sales:invoices"),
            MoadianInvoice.DocumentType.SALE_RETURN: (SaleReturn, send_sale_return, "sales:returns"),
            MoadianInvoice.DocumentType.PURCHASE_INVOICE: (PurchaseInvoice, send_purchase_invoice, "purchases:invoices"),
            MoadianInvoice.DocumentType.PURCHASE_RETURN: (PurchaseReturn, send_purchase_return, "purchases:returns"),
        }
        if document_type not in dispatch:
            messages.error(request, "نوع سند نامعتبر است.")
            return redirect("moadian:invoices")

        model, sender, redirect_url = dispatch[document_type]
        document = get_object_or_404(model, pk=pk, company=self.company)
        try:
            record = sender(document, request=request)
            if record.status == MoadianInvoice.Status.SENT:
                messages.success(request, f"ارسال شد. شماره مرجع: {record.reference_number}")
            else:
                messages.warning(request, f"وضعیت: {record.get_status_display()} — {record.error_message[:200]}")
        except MoadianError as exc:
            messages.error(request, f"خطا در ارسال: {exc}")
        return redirect(redirect_url)

class RefreshStatusView(ScopedMixin, View):
    def post(self, request, pk):
        record = get_object_or_404(MoadianInvoice, pk=pk, company=self.company)
        try:
            refresh_status(record)
            messages.success(request, "وضعیت به‌روزرسانی شد.")
        except MoadianError as exc:
            messages.error(request, f"خطا: {exc}")
        return redirect("moadian:invoices")

class ServerInfoView(ScopedMixin, View):
    template_name = "moadian/server_info.html"

    def get(self, request):
        info = fiscal = error = None
        try:
            config = get_config(self.company)
            client = MoadianClient(config)
            info = client.get_server_info()
            fiscal = client.get_fiscal_info()
        except MoadianError as exc:
            error = str(exc)
        return render(request, self.template_name, {"info": info, "fiscal": fiscal, "error": error})

class EconomicCodeInquiryView(ScopedMixin, View):
    template_name = "moadian/economic_inquiry.html"

    def get(self, request):
        return render(request, self.template_name, {"form": EconomicCodeInquiryForm(), "result": None})

    def post(self, request):
        form = EconomicCodeInquiryForm(request.POST)
        result = error = None
        if form.is_valid():
            try:
                result = validate_economic_code(self.company, form.cleaned_data["economic_code"])
            except MoadianError as exc:
                error = str(exc)
        return render(request, self.template_name, {"form": form, "result": result, "error": error})
