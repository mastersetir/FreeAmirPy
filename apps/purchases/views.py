from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.utils import get_active_company, get_active_fiscal_year
from apps.inventory.models import Warehouse

from .forms import (
    PurchaseInvoiceForm, PurchaseInvoiceLineFormSet, PurchaseInvoicePickerForm,
    PurchaseReturnForm, PurchaseReturnLineFormSet,
)
from .models import PurchaseInvoice, PurchaseReturn, Supplier
from .services import build_purchase_return_lines, post_purchase_invoice, post_purchase_return

class ScopedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.company = get_active_company(request)
        self.fiscal_year = get_active_fiscal_year(request)
        if not self.company:
            messages.error(request, "ابتدا یک شرکت فعال بسازید.")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

class InvoiceListView(ScopedMixin, ListView):
    model = PurchaseInvoice
    template_name = "purchases/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 30

    def get_queryset(self):
        qs = PurchaseInvoice.objects.filter(company=self.company).select_related("supplier")
        if self.fiscal_year:
            qs = qs.filter(fiscal_year=self.fiscal_year)
        return qs

class InvoiceCreateView(ScopedMixin, View):
    template_name = "purchases/invoice_form.html"

    def get(self, request):
        form = PurchaseInvoiceForm(initial={"number": self._next_number()})
        form.fields["supplier"].queryset = Supplier.objects.filter(company=self.company)
        formset = PurchaseInvoiceLineFormSet()
        self._limit(formset)
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request):
        form = PurchaseInvoiceForm(request.POST)
        form.fields["supplier"].queryset = Supplier.objects.filter(company=self.company)
        formset = PurchaseInvoiceLineFormSet(request.POST)
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
            messages.success(request, "فاکتور خرید ساخته شد.")
            return redirect("purchases:invoices")
        return render(request, self.template_name, {"form": form, "formset": formset})

    def _next_number(self):
        last = PurchaseInvoice.objects.filter(fiscal_year=self.fiscal_year).order_by("-id").first() if self.fiscal_year else None
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
        inv = get_object_or_404(PurchaseInvoice, pk=pk, company=self.company)
        try:
            post_purchase_invoice(inv, request=request)
            messages.success(request, "سند خرید ثبت شد.")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا: {exc}")
        return redirect("purchases:invoices")

class ReturnListView(ScopedMixin, ListView):
    model = PurchaseReturn
    template_name = "purchases/return_list.html"
    context_object_name = "returns"
    paginate_by = 30

    def get_queryset(self):
        qs = PurchaseReturn.objects.filter(company=self.company).select_related("invoice", "invoice__supplier")
        if self.fiscal_year:
            qs = qs.filter(fiscal_year=self.fiscal_year)
        return qs

class ReturnPickerView(ScopedMixin, View):
    template_name = "purchases/return_picker.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PurchaseInvoicePickerForm(company=self.company)})

    def post(self, request):
        form = PurchaseInvoicePickerForm(request.POST, company=self.company)
        if form.is_valid():
            invoice = form.cleaned_data["invoice"]
            if not self.fiscal_year:
                messages.error(request, "سال مالی فعالی وجود ندارد.")
                return redirect("purchases:returns")
            with transaction.atomic():
                ret = PurchaseReturn.objects.create(
                    company=self.company, fiscal_year=self.fiscal_year,
                    number=self._next_number(), date=invoice.date,
                    invoice=invoice, status=PurchaseReturn.Status.DRAFT,
                )
                build_purchase_return_lines(ret)
            if not ret.lines.exists():
                ret.delete()
                messages.warning(request, "همه‌ی اقلام این فاکتور قبلاً برگشت داده شده‌اند.")
                return redirect("purchases:returns")
            return redirect("purchases:return_edit", pk=ret.pk)
        return render(request, self.template_name, {"form": form})

    def _next_number(self):
        last = PurchaseReturn.objects.filter(fiscal_year=self.fiscal_year).order_by("-id").first() if self.fiscal_year else None
        try:
            n = int(last.number.split("-")[-1]) if last else 0
        except (ValueError, TypeError, AttributeError):
            n = 0
        return f"{n + 1:05d}"

class ReturnEditView(ScopedMixin, View):
    template_name = "purchases/return_form.html"

    def get(self, request, pk):
        ret = get_object_or_404(PurchaseReturn, pk=pk, company=self.company)
        if ret.status != PurchaseReturn.Status.DRAFT:
            messages.error(request, "این برگشت قبلاً ثبت شده است.")
            return redirect("purchases:returns")
        return render(request, self.template_name, {
            "form": PurchaseReturnForm(instance=ret),
            "formset": PurchaseReturnLineFormSet(instance=ret),
            "ret": ret,
        })

    def post(self, request, pk):
        ret = get_object_or_404(PurchaseReturn, pk=pk, company=self.company)
        if ret.status != PurchaseReturn.Status.DRAFT:
            messages.error(request, "این برگشت قبلاً ثبت شده است.")
            return redirect("purchases:returns")
        form = PurchaseReturnForm(request.POST, instance=ret)
        formset = PurchaseReturnLineFormSet(request.POST, instance=ret)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                ret.recalc_totals()
            messages.success(request, "برگشت خرید ذخیره شد.")
            return redirect("purchases:returns")
        return render(request, self.template_name, {"form": form, "formset": formset, "ret": ret})

class ReturnPostView(ScopedMixin, View):
    def post(self, request, pk):
        ret = get_object_or_404(PurchaseReturn, pk=pk, company=self.company)
        try:
            journal, inv_credit = post_purchase_return(ret, request=request)
            messages.success(request, f"برگشت خرید ثبت شد. کاهش موجودی: {inv_credit:,.2f}")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا: {exc}")
        return redirect("purchases:returns")
