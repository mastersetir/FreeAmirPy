from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.utils import get_active_company, get_active_fiscal_year
from apps.inventory.models import Warehouse

from .forms import (
    InvoicePickerForm, SaleInvoiceForm, SaleInvoiceLineFormSet,
    SaleReturnForm, SaleReturnLineFormSet,
)
from .models import Customer, SaleInvoice, SaleReturn
from .services import build_sale_return_lines, post_sale_invoice, post_sale_return

class ScopedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.company = get_active_company(request)
        self.fiscal_year = get_active_fiscal_year(request)
        if not self.company:
            messages.error(request, "ابتدا یک شرکت فعال بسازید.")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

class InvoiceListView(ScopedMixin, ListView):
    model = SaleInvoice
    template_name = "sales/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 30

    def get_queryset(self):
        qs = SaleInvoice.objects.filter(company=self.company).select_related("customer")
        if self.fiscal_year:
            qs = qs.filter(fiscal_year=self.fiscal_year)
        return qs

class InvoiceCreateView(ScopedMixin, View):
    template_name = "sales/invoice_form.html"

    def get(self, request):
        form = SaleInvoiceForm(initial={"number": self._next_number()})
        form.fields["customer"].queryset = Customer.objects.filter(company=self.company)
        formset = SaleInvoiceLineFormSet()
        self._limit(formset)
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request):
        form = SaleInvoiceForm(request.POST)
        form.fields["customer"].queryset = Customer.objects.filter(company=self.company)
        formset = SaleInvoiceLineFormSet(request.POST)
        self._limit(formset)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                inv = form.save(commit=False)
                inv.company = self.company
                inv.fiscal_year = self.fiscal_year
                inv.save()
                formset.instance = inv
                formset.save()
                inv.recalc_totals()
            messages.success(request, "فاکتور ساخته شد.")
            return redirect("sales:invoices")
        return render(request, self.template_name, {"form": form, "formset": formset})

    def _next_number(self):
        last = SaleInvoice.objects.filter(fiscal_year=self.fiscal_year).order_by("-id").first() if self.fiscal_year else None
        try:
            n = int(last.number.split("-")[-1]) if last else 0
        except (ValueError, TypeError, AttributeError):
            n = 0
        return f"{n + 1:05d}"

    def _limit(self, formset):
        for f in formset.forms:
            f.fields["product"].queryset = f.fields["product"].queryset.filter(company=self.company)
            f.fields["warehouse"].queryset = Warehouse.objects.filter(company=self.company, is_active=True)

class InvoicePostView(ScopedMixin, View):
    def post(self, request, pk):
        inv = get_object_or_404(SaleInvoice, pk=pk, company=self.company)
        try:
            journal, cogs = post_sale_invoice(inv, request=request)
            messages.success(request, f"سند حسابداری ثبت شد. بهای تمام شده: {cogs:,.2f}")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا: {exc}")
        return redirect("sales:invoices")

class ReturnListView(ScopedMixin, ListView):
    model = SaleReturn
    template_name = "sales/return_list.html"
    context_object_name = "returns"
    paginate_by = 30

    def get_queryset(self):
        qs = SaleReturn.objects.filter(company=self.company).select_related("invoice", "invoice__customer")
        if self.fiscal_year:
            qs = qs.filter(fiscal_year=self.fiscal_year)
        return qs

class ReturnPickerView(ScopedMixin, View):
    template_name = "sales/return_picker.html"

    def get(self, request):
        return render(request, self.template_name, {"form": InvoicePickerForm(company=self.company)})

    def post(self, request):
        form = InvoicePickerForm(request.POST, company=self.company)
        if form.is_valid():
            invoice = form.cleaned_data["invoice"]
            if not self.fiscal_year:
                messages.error(request, "سال مالی فعالی وجود ندارد.")
                return redirect("sales:returns")
            with transaction.atomic():
                ret = SaleReturn.objects.create(
                    company=self.company, fiscal_year=self.fiscal_year,
                    number=self._next_number(), date=invoice.date,
                    invoice=invoice, status=SaleReturn.Status.DRAFT,
                )
                build_sale_return_lines(ret)
            if not ret.lines.exists():
                ret.delete()
                messages.warning(request, "همه‌ی اقلام این فاکتور قبلاً برگشت داده شده‌اند.")
                return redirect("sales:returns")
            return redirect("sales:return_edit", pk=ret.pk)
        return render(request, self.template_name, {"form": form})

    def _next_number(self):
        last = SaleReturn.objects.filter(fiscal_year=self.fiscal_year).order_by("-id").first() if self.fiscal_year else None
        try:
            n = int(last.number.split("-")[-1]) if last else 0
        except (ValueError, TypeError, AttributeError):
            n = 0
        return f"{n + 1:05d}"

class ReturnEditView(ScopedMixin, View):
    template_name = "sales/return_form.html"

    def get(self, request, pk):
        ret = get_object_or_404(SaleReturn.objects.select_related("invoice"), pk=pk, company=self.company)
        if ret.status != SaleReturn.Status.DRAFT:
            messages.error(request, "این برگشت قبلاً ثبت شده است.")
            return redirect("sales:returns")
        return render(request, self.template_name, {
            "form": SaleReturnForm(instance=ret),
            "formset": SaleReturnLineFormSet(instance=ret),
            "ret": ret,
        })

    def post(self, request, pk):
        ret = get_object_or_404(SaleReturn, pk=pk, company=self.company)
        if ret.status != SaleReturn.Status.DRAFT:
            messages.error(request, "این برگشت قبلاً ثبت شده است.")
            return redirect("sales:returns")
        form = SaleReturnForm(request.POST, instance=ret)
        formset = SaleReturnLineFormSet(request.POST, instance=ret)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                ret.recalc_totals()
            messages.success(request, "برگشت ذخیره شد. برای نهایی‌سازی «ثبت» را بزنید.")
            return redirect("sales:returns")
        return render(request, self.template_name, {"form": form, "formset": formset, "ret": ret})

class ReturnPostView(ScopedMixin, View):
    def post(self, request, pk):
        ret = get_object_or_404(SaleReturn, pk=pk, company=self.company)
        try:
            journal, cogs = post_sale_return(ret, request=request)
            messages.success(request, f"برگشت ثبت شد. برگشت COGS: {cogs:,.2f}")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا: {exc}")
        return redirect("sales:returns")
