from django import forms
from .models import Attendance, Employee, PayrollConfig, PayrollRun

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = (
            "code", "first_name", "last_name", "national_id", "father_name",
            "position", "employee_type", "hire_date", "termination_date", "is_active",
            "base_salary", "housing_allowance", "food_allowance",
            "marriage_allowance", "children_count", "children_allowance_per_child",
            "insurance_number", "bank_name", "bank_account", "iban",
        )
        widgets = {
            f: forms.TextInput(attrs={"class": "form-input"}) for f in (
                "code", "first_name", "last_name", "national_id", "father_name",
                "position", "insurance_number", "bank_name", "bank_account", "iban",
            )
        }
        widgets.update({
            "employee_type": forms.Select(attrs={"class": "form-input"}),
            "hire_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "termination_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "base_salary": forms.NumberInput(attrs={"class": "form-input", "step": "1000"}),
            "housing_allowance": forms.NumberInput(attrs={"class": "form-input", "step": "1000"}),
            "food_allowance": forms.NumberInput(attrs={"class": "form-input", "step": "1000"}),
            "marriage_allowance": forms.NumberInput(attrs={"class": "form-input", "step": "1000"}),
            "children_allowance_per_child": forms.NumberInput(attrs={"class": "form-input", "step": "1000"}),
        })

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ("employee", "date", "leave_type", "check_in", "check_out",
                  "worked_hours", "overtime_hours", "note")
        widgets = {
            "employee": forms.Select(attrs={"class": "form-input"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "leave_type": forms.Select(attrs={"class": "form-input"}),
            "check_in": forms.TimeInput(attrs={"class": "form-input", "type": "time"}),
            "check_out": forms.TimeInput(attrs={"class": "form-input", "type": "time"}),
            "worked_hours": forms.NumberInput(attrs={"class": "form-input", "step": "0.25"}),
            "overtime_hours": forms.NumberInput(attrs={"class": "form-input", "step": "0.25"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["employee"].queryset = Employee.objects.filter(company=company, is_active=True)

class PayrollRunForm(forms.ModelForm):
    class Meta:
        model = PayrollRun
        fields = ("year", "month", "period_start", "period_end", "notes")
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-input"}),
            "month": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 12}),
            "period_start": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "period_end": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }

    def clean(self):
        data = super().clean()
        if data.get("period_start") and data.get("period_end"):
            if data["period_start"] >= data["period_end"]:
                raise forms.ValidationError("تاریخ شروع باید قبل از پایان باشد.")
        return data

class PayrollConfigForm(forms.ModelForm):
    class Meta:
        model = PayrollConfig
        fields = ("insurance_employee_rate", "insurance_employer_rate",
                  "overtime_premium_percent", "standard_monthly_hours",
                  "insurance_cap_amount")
        widgets = {
            f: forms.NumberInput(attrs={"class": "form-input", "step": "0.01"})
            for f in ("insurance_employee_rate", "insurance_employer_rate",
                      "overtime_premium_percent", "standard_monthly_hours",
                      "insurance_cap_amount")
        }
