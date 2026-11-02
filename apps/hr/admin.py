from django.contrib import admin
from .models import Attendance, Employee, PayrollConfig, PayrollRun, Payslip, TaxBracket

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "national_id", "position", "employee_type",
                    "base_salary", "hire_date", "is_active")
    list_filter = ("company", "employee_type", "is_active")
    search_fields = ("code", "first_name", "last_name", "national_id")

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("date", "employee", "leave_type", "worked_hours", "overtime_hours")
    list_filter = ("company", "leave_type", "date")
    search_fields = ("employee__code", "employee__first_name", "employee__last_name")

class PayslipInline(admin.TabularInline):
    model = Payslip
    extra = 0
    readonly_fields = ("employee", "gross_pay", "net_pay", "income_tax")
    fields = ("employee", "days_worked", "gross_pay", "insurance_employee", "income_tax", "net_pay")
    can_delete = False

@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ("company", "year", "month", "status", "total_gross", "total_net", "journal")
    list_filter = ("company", "status", "year")
    inlines = [PayslipInline]
    readonly_fields = ("total_gross", "total_insurance_employee", "total_insurance_employer",
                       "total_income_tax", "total_net")

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ("employee", "payroll_run", "gross_pay", "insurance_employee",
                    "income_tax", "net_pay")
    list_filter = ("payroll_run__year", "payroll_run__month", "employee__company")
    search_fields = ("employee__code", "employee__first_name", "employee__last_name")
    readonly_fields = ("tax_breakdown", "gross_pay", "net_pay", "taxable_income")

@admin.register(PayrollConfig)
class PayrollConfigAdmin(admin.ModelAdmin):
    list_display = ("company", "insurance_employee_rate", "insurance_employer_rate",
                    "overtime_premium_percent", "standard_monthly_hours", "insurance_cap_amount")

@admin.register(TaxBracket)
class TaxBracketAdmin(admin.ModelAdmin):
    list_display = ("year", "order", "min_amount", "max_amount", "rate")
    list_filter = ("year",)
    ordering = ("year", "order")
