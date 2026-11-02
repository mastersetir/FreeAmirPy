from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.utils import get_active_company, get_active_fiscal_year

from .forms import AttendanceForm, EmployeeForm, PayrollConfigForm, PayrollRunForm
from .models import Attendance, Employee, PayrollRun
from .services import calculate_payroll, get_config, post_payroll

class ScopedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.company = get_active_company(request)
        self.fiscal_year = get_active_fiscal_year(request)
        if not self.company:
            messages.error(request, "ابتدا یک شرکت فعال بسازید.")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

class EmployeeListView(ScopedMixin, ListView):
    model = Employee
    template_name = "hr/employee_list.html"
    context_object_name = "employees"
    paginate_by = 50

    def get_queryset(self):
        return Employee.objects.filter(company=self.company).order_by("code")

class EmployeeCreateView(ScopedMixin, View):
    template_name = "hr/employee_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": EmployeeForm(), "title": "کارمند جدید"})

    def post(self, request):
        form = EmployeeForm(request.POST)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.company = self.company
            emp.save()
            messages.success(request, "کارمند ایجاد شد.")
            return redirect("hr:employees")
        return render(request, self.template_name, {"form": form, "title": "کارمند جدید"})

class EmployeeEditView(ScopedMixin, View):
    template_name = "hr/employee_form.html"

    def get(self, request, pk):
        emp = get_object_or_404(Employee, pk=pk, company=self.company)
        return render(request, self.template_name,
                      {"form": EmployeeForm(instance=emp), "title": f"ویرایش {emp.full_name}"})

    def post(self, request, pk):
        emp = get_object_or_404(Employee, pk=pk, company=self.company)
        form = EmployeeForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, "کارمند ویرایش شد.")
            return redirect("hr:employees")
        return render(request, self.template_name, {"form": form, "title": f"ویرایش {emp.full_name}"})

class AttendanceListView(ScopedMixin, ListView):
    model = Attendance
    template_name = "hr/attendance_list.html"
    context_object_name = "attendances"
    paginate_by = 50

    def get_queryset(self):
        qs = Attendance.objects.filter(company=self.company).select_related("employee")
        emp = self.request.GET.get("employee")
        if emp:
            qs = qs.filter(employee_id=emp)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["employees"] = Employee.objects.filter(company=self.company, is_active=True)
        return ctx

class AttendanceCreateView(ScopedMixin, View):
    template_name = "hr/attendance_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": AttendanceForm(company=self.company)})

    def post(self, request):
        form = AttendanceForm(request.POST, company=self.company)
        if form.is_valid():
            att = form.save(commit=False)
            att.company = self.company
            att.save()
            messages.success(request, "حضور ثبت شد.")
            return redirect("hr:attendance")
        return render(request, self.template_name, {"form": form})

class PayrollListView(ScopedMixin, ListView):
    model = PayrollRun
    template_name = "hr/payroll_list.html"
    context_object_name = "payrolls"
    paginate_by = 20

    def get_queryset(self):
        return PayrollRun.objects.filter(company=self.company).order_by("-year", "-month")

class PayrollCreateView(ScopedMixin, View):
    template_name = "hr/payroll_form.html"

    def get(self, request):
        if not self.fiscal_year:
            messages.error(request, "سال مالی فعالی وجود ندارد.")
            return redirect("hr:payrolls")
        return render(request, self.template_name, {"form": PayrollRunForm()})

    def post(self, request):
        form = PayrollRunForm(request.POST)
        if form.is_valid():
            pr = form.save(commit=False)
            pr.company = self.company
            pr.fiscal_year = self.fiscal_year
            pr.save()
            messages.success(request, "دوره‌ی حقوق ایجاد شد. برای محاسبه دکمه‌ی «محاسبه» را بزنید.")
            return redirect("hr:payroll_detail", pk=pr.pk)
        return render(request, self.template_name, {"form": form})

class PayrollDetailView(ScopedMixin, View):
    template_name = "hr/payroll_detail.html"

    def get(self, request, pk):
        pr = get_object_or_404(PayrollRun, pk=pk, company=self.company)
        return render(request, self.template_name, {
            "payroll": pr,
            "payslips": pr.payslips.select_related("employee").order_by("employee__code"),
        })

class PayrollCalculateView(ScopedMixin, View):
    def post(self, request, pk):
        pr = get_object_or_404(PayrollRun, pk=pk, company=self.company)
        try:
            calculate_payroll(pr, request=request)
            messages.success(request, f"{pr.payslips.count()} فیش محاسبه شد.")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا: {exc}")
        return redirect("hr:payroll_detail", pk=pk)

class PayrollPostView(ScopedMixin, View):
    def post(self, request, pk):
        pr = get_object_or_404(PayrollRun, pk=pk, company=self.company)
        try:
            post_payroll(pr, request=request)
            messages.success(request, f"سند حقوق صادر شد: {pr.journal.number}")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا: {exc}")
        return redirect("hr:payroll_detail", pk=pk)

class PayrollConfigView(ScopedMixin, View):
    template_name = "hr/payroll_config.html"

    def get(self, request):
        cfg = get_config(self.company)
        return render(request, self.template_name, {"form": PayrollConfigForm(instance=cfg)})

    def post(self, request):
        cfg = get_config(self.company)
        form = PayrollConfigForm(request.POST, instance=cfg)
        if form.is_valid():
            form.save()
            messages.success(request, "تنظیمات ذخیره شد.")
            return redirect("hr:payroll_config")
        return render(request, self.template_name, {"form": form})
