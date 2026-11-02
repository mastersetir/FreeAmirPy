from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.utils import get_active_company

from .forms import StockInForm, WarehouseForm
from .models import StockBalance, StockMove, Warehouse
from .services import receive_stock

class ScopedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.company = get_active_company(request)
        if not self.company:
            messages.error(request, "ابتدا یک شرکت فعال انتخاب کنید.")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

class WarehouseListView(ScopedMixin, ListView):
    model = Warehouse
    template_name = "inventory/warehouse_list.html"
    context_object_name = "warehouses"

    def get_queryset(self):
        return Warehouse.objects.filter(company=self.company).order_by("code")

class WarehouseCreateView(ScopedMixin, View):
    template_name = "inventory/warehouse_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": WarehouseForm()})

    def post(self, request):
        form = WarehouseForm(request.POST)
        if form.is_valid():
            wh = form.save(commit=False)
            wh.company = self.company
            wh.save()
            messages.success(request, "انبار ایجاد شد.")
            return redirect("inventory:warehouses")
        return render(request, self.template_name, {"form": form})

class StockMoveListView(ScopedMixin, ListView):
    model = StockMove
    template_name = "inventory/stock_moves.html"
    context_object_name = "moves"
    paginate_by = 50

    def get_queryset(self):
        qs = StockMove.objects.filter(company=self.company).select_related("warehouse", "product")
        wh = self.request.GET.get("warehouse")
        if wh:
            qs = qs.filter(warehouse_id=wh)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["warehouses"] = Warehouse.objects.filter(company=self.company)
        return ctx

class StockInView(ScopedMixin, View):
    template_name = "inventory/stock_in.html"

    def get(self, request):
        return render(request, self.template_name, {"form": StockInForm(company=self.company)})

    def post(self, request):
        form = StockInForm(request.POST, company=self.company)
        if form.is_valid():
            try:
                receive_stock(
                    warehouse=form.cleaned_data["warehouse"],
                    product=form.cleaned_data["product"],
                    qty=form.cleaned_data["quantity"],
                    unit_cost=form.cleaned_data["unit_cost"],
                    date=form.cleaned_data["date"],
                    reference=form.cleaned_data["reference"],
                    note=form.cleaned_data["note"],
                )
                messages.success(request, "ورود کالا ثبت شد.")
                return redirect("inventory:moves")
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"خطا: {exc}")
        return render(request, self.template_name, {"form": form})

class BalanceListView(ScopedMixin, ListView):
    model = StockBalance
    template_name = "inventory/balances.html"
    context_object_name = "balances"

    def get_queryset(self):
        return (
            StockBalance.objects.filter(company=self.company, quantity__gt=0)
            .select_related("warehouse", "product")
            .order_by("warehouse__code", "product__code")
        )
