"""منابع انسانی: کارمند، حضور و غیاب، دوره‌ی حقوق، فیش حقوقی، پله‌های مالیات."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from apps.core.models import CompanyScopedModel

class Employee(CompanyScopedModel):
    class EmployeeType(models.TextChoices):
        PERMANENT = "permanent", "رسمی"
        CONTRACT = "contract", "قراردادی"
        TEMPORARY = "temporary", "موقت"

    code = models.CharField("کد کارمند", max_length=20)
    first_name = models.CharField("نام", max_length=100)
    last_name = models.CharField("نام خانوادگی", max_length=100)
    national_id = models.CharField("کد ملی", max_length=10)
    father_name = models.CharField("نام پدر", max_length=100, blank=True)
    birth_date = models.DateField("تاریخ تولد", null=True, blank=True)
    birth_certificate_number = models.CharField("شماره شناسنامه", max_length=20, blank=True)

    position = models.CharField("سمت", max_length=100, blank=True)
    employee_type = models.CharField(max_length=20, choices=EmployeeType.choices, default=EmployeeType.CONTRACT)

    hire_date = models.DateField("تاریخ استخدام")
    termination_date = models.DateField("تاریخ پایان همکاری", null=True, blank=True)

    base_salary = models.DecimalField("حقوق پایه (ماهانه)", max_digits=20, decimal_places=2, default=Decimal("0"))
    housing_allowance = models.DecimalField("حق مسکن", max_digits=20, decimal_places=2, default=Decimal("0"))
    food_allowance = models.DecimalField("کمک هزینه خواربار", max_digits=20, decimal_places=2, default=Decimal("0"))
    marriage_allowance = models.DecimalField("حق تأهل", max_digits=20, decimal_places=2, default=Decimal("0"))
    children_count = models.PositiveSmallIntegerField("تعداد فرزند", default=0)
    children_allowance_per_child = models.DecimalField(
        "حق اولاد (هر فرزند)", max_digits=20, decimal_places=2, default=Decimal("0"))

    insurance_number = models.CharField("شماره بیمه", max_length=30, blank=True)
    bank_name = models.CharField("نام بانک", max_length=100, blank=True)
    bank_account = models.CharField("شماره حساب", max_length=30, blank=True)
    iban = models.CharField("شبا", max_length=26, blank=True)
    annual_leave_balance = models.DecimalField("مانده مرخصی (روز)", max_digits=6, decimal_places=2, default=Decimal("0"))

    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        unique_together = [("company", "code"), ("company", "national_id")]
        ordering = ["code"]
        verbose_name = "کارمند"
        verbose_name_plural = "کارمندان"

    def __str__(self) -> str:
        return f"{self.code} — {self.full_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def monthly_allowances(self) -> Decimal:
        return (self.housing_allowance + self.food_allowance + self.marriage_allowance
                + self.children_allowance_per_child * self.children_count)

class Attendance(CompanyScopedModel):
    class LeaveType(models.TextChoices):
        PRESENT = "present", "حاضر"
        ABSENT = "absent", "غایب"
        SICK = "sick", "استعلاجی"
        ANNUAL = "annual", "مرخصی استحقاقی"
        UNPAID = "unpaid", "مرخصی بدون حقوق"
        HOLIDAY = "holiday", "تعطیل"
        MISSION = "mission", "مأموریت"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField("تاریخ")
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.PRESENT)
    check_in = models.TimeField("ورود", null=True, blank=True)
    check_out = models.TimeField("خروج", null=True, blank=True)
    worked_hours = models.DecimalField("ساعت کارکرد", max_digits=5, decimal_places=2, default=Decimal("0"))
    overtime_hours = models.DecimalField("ساعت اضافه‌کاری", max_digits=5, decimal_places=2, default=Decimal("0"))
    note = models.TextField("توضیحات", blank=True)

    class Meta:
        unique_together = [("employee", "date")]
        ordering = ["-date"]
        verbose_name = "حضور و غیاب"
        verbose_name_plural = "حضور و غیاب"
        indexes = [models.Index(fields=["employee", "date"])]

    def __str__(self) -> str:
        return f"{self.employee.code} — {self.date} ({self.get_leave_type_display()})"

    def clean(self):
        if self.worked_hours < 0 or self.overtime_hours < 0:
            raise ValidationError("ساعت کارکرد و اضافه‌کاری نمی‌توانند منفی باشند.")
        if self.worked_hours > 24 or self.overtime_hours > 12:
            raise ValidationError("ساعت کارکرد یا اضافه‌کاری بیش از حد مجاز.")

class PayrollRun(CompanyScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        CALCULATED = "calculated", "محاسبه‌شده"
        POSTED = "posted", "ثبت‌شده"

    fiscal_year = models.ForeignKey("core.FiscalYear", on_delete=models.PROTECT, related_name="payroll_runs")
    year = models.PositiveSmallIntegerField("سال (جلالی)")
    month = models.PositiveSmallIntegerField("ماه (جلالی)")
    period_start = models.DateField("شروع دوره")
    period_end = models.DateField("پایان دوره")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    journal = models.ForeignKey("accounting.Journal", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")
    notes = models.TextField("یادداشت", blank=True)

    total_gross = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_insurance_employee = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_insurance_employer = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_income_tax = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_other_deductions = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    total_net = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("company", "year", "month")]
        ordering = ["-year", "-month"]
        verbose_name = "دوره‌ی حقوق"
        verbose_name_plural = "دوره‌های حقوق"

    def __str__(self) -> str:
        return f"{self.company.name} — {self.year}/{self.month:02d}"

    def recalc_totals(self):
        agg = self.payslips.aggregate(
            g=Sum("gross_pay"), ie=Sum("insurance_employee"),
            ir=Sum("insurance_employer"), t=Sum("income_tax"),
            o=Sum("other_deductions"), n=Sum("net_pay"),
        )
        for field, key in [
            ("total_gross", "g"), ("total_insurance_employee", "ie"),
            ("total_insurance_employer", "ir"), ("total_income_tax", "t"),
            ("total_other_deductions", "o"), ("total_net", "n"),
        ]:
            setattr(self, field, agg[key] or Decimal("0"))
        self.save(update_fields=[
            "total_gross", "total_insurance_employee", "total_insurance_employer",
            "total_income_tax", "total_other_deductions", "total_net",
        ])

class Payslip(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="payslips")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payslips")

    days_worked = models.DecimalField("روزهای کارکرد", max_digits=5, decimal_places=2, default=Decimal("0"))
    overtime_hours = models.DecimalField("ساعت اضافه‌کاری", max_digits=6, decimal_places=2, default=Decimal("0"))

    base_salary = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    housing_allowance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    food_allowance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    marriage_allowance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    children_allowance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    overtime_pay = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))

    gross_pay = models.DecimalField("جمع حقوق و مزایا", max_digits=20, decimal_places=2, default=Decimal("0"))
    insurance_employee = models.DecimalField("بیمه سهم کارمند", max_digits=20, decimal_places=2, default=Decimal("0"))
    insurance_employer = models.DecimalField("بیمه سهم کارفرما", max_digits=20, decimal_places=2, default=Decimal("0"))
    income_tax = models.DecimalField("مالیات بر درآمد", max_digits=20, decimal_places=2, default=Decimal("0"))
    other_deductions = models.DecimalField("سایر کسور", max_digits=20, decimal_places=2, default=Decimal("0"))
    net_pay = models.DecimalField("حقوق خالص", max_digits=20, decimal_places=2, default=Decimal("0"))

    taxable_income = models.DecimalField("درآمد مشمول مالیات", max_digits=20, decimal_places=2, default=Decimal("0"))
    tax_breakdown = models.JSONField("جزئیات محاسبه مالیات", default=list, blank=True)

    note = models.TextField("یادداشت", blank=True)

    class Meta:
        unique_together = [("payroll_run", "employee")]
        ordering = ["employee__code"]
        verbose_name = "فیش حقوقی"
        verbose_name_plural = "فیش‌های حقوقی"

    def __str__(self) -> str:
        return f"{self.employee.full_name} — {self.payroll_run.year}/{self.payroll_run.month:02d}"

class PayrollConfig(CompanyScopedModel):
    insurance_employee_rate = models.DecimalField(
        "نرخ بیمه کارمند (٪)", max_digits=5, decimal_places=2, default=Decimal("7"))
    insurance_employer_rate = models.DecimalField(
        "نرخ بیمه کارفرما (٪)", max_digits=5, decimal_places=2, default=Decimal("23"))
    overtime_premium_percent = models.DecimalField(
        "درصد اضافه‌کاری", max_digits=5, decimal_places=2, default=Decimal("40"),
        help_text="مطابق قانون کار ایران: ۴۰٪ اضافه بر نرخ عادی")
    standard_monthly_hours = models.DecimalField(
        "ساعت کار ماهانه", max_digits=6, decimal_places=2, default=Decimal("220"))
    insurance_cap_amount = models.DecimalField(
        "سقف مبلغ بیمه (ماهانه)", max_digits=20, decimal_places=2, default=Decimal("0"),
        help_text="صفر یعنی بدون سقف")

    class Meta:
        verbose_name = "تنظیمات حقوق و دستمزد"
        verbose_name_plural = "تنظیمات حقوق و دستمزد"
        unique_together = [("company",)]

    def __str__(self) -> str:
        return f"تنظیمات حقوق — {self.company.name}"

class TaxBracket(models.Model):
    year = models.PositiveSmallIntegerField("سال (جلالی)")
    order = models.PositiveSmallIntegerField("ترتیب")
    min_amount = models.DecimalField("حداقل درآمد ماهانه", max_digits=20, decimal_places=2)
    max_amount = models.DecimalField(
        "حداکثر درآمد ماهانه", max_digits=20, decimal_places=2, null=True, blank=True,
        help_text="خالی = بدون سقف")
    rate = models.DecimalField("نرخ (٪)", max_digits=5, decimal_places=2)

    class Meta:
        unique_together = [("year", "order")]
        ordering = ["year", "order"]
        verbose_name = "پله‌ی مالیات"
        verbose_name_plural = "پله‌های مالیات"

    def __str__(self) -> str:
        if self.max_amount:
            return f"{self.year} — {self.min_amount} تا {self.max_amount} @ {self.rate}٪"
        return f"{self.year} — بالای {self.min_amount} @ {self.rate}٪"
