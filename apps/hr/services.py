"""سرویس‌های حقوق و دستمزد: محاسبه، ثبت، صدور سند."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounting.models import Account, Journal, JournalEntry
from apps.core.activity import log_activity

from .models import Attendance, Employee, PayrollConfig, PayrollRun, Payslip, TaxBracket


def get_config(company) -> PayrollConfig:
    cfg, _ = PayrollConfig.objects.get_or_create(company=company)
    return cfg


def ensure_account(company, code_key: str, default_code: str,
                   default_name: str, default_type: str) -> Account:
    """دریافت یا ساخت حساب با کلید COA. جایگزین امن برای get_coa_account."""
    code = settings.COA.get(code_key, default_code)
    account, _ = Account.objects.get_or_create(
        company=company, code=code,
        defaults={"name": default_name, "account_type": default_type, "is_postable": True},
    )
    return account


def get_tax_brackets(year: int) -> list[TaxBracket]:
    qs = TaxBracket.objects.filter(year=year).order_by("order")
    if not qs.exists():
        qs = TaxBracket.objects.filter(year=1403).order_by("order")
    if not qs.exists():
        raise ValidationError(
            f"پله‌های مالیات برای سال {year} تعریف نشده است. "
            f"ابتدا از دستور seed_tax_brackets استفاده کنید."
        )
    return list(qs)


def calculate_income_tax(taxable_amount: Decimal, brackets: list[TaxBracket]) -> tuple[Decimal, list]:
    tax = Decimal("0")
    breakdown = []
    for b in brackets:
        if taxable_amount <= b.min_amount:
            break
        if b.max_amount is None:
            portion = taxable_amount - b.min_amount
        else:
            portion = min(taxable_amount, b.max_amount) - b.min_amount
        if portion <= 0:
            continue
        tax_portion = (portion * b.rate / Decimal("100")).quantize(Decimal("0.01"))
        tax += tax_portion
        breakdown.append({
            "min": str(b.min_amount),
            "max": str(b.max_amount) if b.max_amount else None,
            "rate": str(b.rate),
            "portion": str(portion),
            "tax": str(tax_portion),
        })
    return tax, breakdown


def _compute_worked_days(employee: Employee, payroll_run: PayrollRun) -> tuple[Decimal, Decimal]:
    """محاسبه‌ی روزهای کارکرد و اضافه‌کاری."""
    attendance = Attendance.objects.filter(
        employee=employee,
        date__gte=payroll_run.period_start,
        date__lte=payroll_run.period_end,
    )
    has_attendance = attendance.exists()

    paid_types = {
        Attendance.LeaveType.PRESENT,
        Attendance.LeaveType.SICK,
        Attendance.LeaveType.ANNUAL,
        Attendance.LeaveType.MISSION,
        Attendance.LeaveType.HOLIDAY,
    }

    if has_attendance:
        worked_days = Decimal("0")
        overtime_hours = Decimal("0")
        for a in attendance:
            if a.leave_type in paid_types:
                worked_days += Decimal("1")
            overtime_hours += a.overtime_hours or Decimal("0")
        return worked_days, overtime_hours

    # هیچ رکوردی نیست — فرض کل ماه، با کسر ایام قبل از استخدام/بعد از پایان کار
    period_days = (payroll_run.period_end - payroll_run.period_start).days + 1
    start = max(employee.hire_date, payroll_run.period_start)
    end = payroll_run.period_end
    if employee.termination_date and employee.termination_date < end:
        end = employee.termination_date
    actual = max(0, (end - start).days + 1)
    worked = (Decimal("30") * Decimal(actual) / Decimal(period_days)).quantize(Decimal("0.01"))
    return worked, Decimal("0")


def calculate_payslip(*, employee: Employee, payroll_run: PayrollRun) -> Payslip:
    cfg = get_config(employee.company)
    brackets = get_tax_brackets(payroll_run.year)

    worked_days, overtime_hours = _compute_worked_days(employee, payroll_run)

    base_prorated = (employee.base_salary * worked_days / Decimal("30")).quantize(Decimal("0.01"))

    housing = employee.housing_allowance
    food = employee.food_allowance
    marriage = employee.marriage_allowance
    children = employee.children_allowance_per_child * employee.children_count

    hourly_rate = (
        employee.base_salary / cfg.standard_monthly_hours
        if cfg.standard_monthly_hours > 0 else Decimal("0")
    )
    overtime_pay = (
        hourly_rate * (Decimal("1") + cfg.overtime_premium_percent / Decimal("100")) * overtime_hours
    ).quantize(Decimal("0.01"))

    gross_pay = base_prorated + housing + food + marriage + children + overtime_pay

    ins_base = gross_pay
    if cfg.insurance_cap_amount > 0:
        ins_base = min(gross_pay, cfg.insurance_cap_amount)
    insurance_employee = (ins_base * cfg.insurance_employee_rate / Decimal("100")).quantize(Decimal("0.01"))
    insurance_employer = (ins_base * cfg.insurance_employer_rate / Decimal("100")).quantize(Decimal("0.01"))

    taxable = gross_pay - insurance_employee
    if taxable < 0:
        taxable = Decimal("0")
    tax, breakdown = calculate_income_tax(taxable, brackets)

    other = Decimal("0")
    net_pay = gross_pay - insurance_employee - tax - other

    payslip, _ = Payslip.objects.update_or_create(
        payroll_run=payroll_run, employee=employee,
        defaults={
            "days_worked": worked_days,
            "overtime_hours": overtime_hours,
            "base_salary": base_prorated,
            "housing_allowance": housing,
            "food_allowance": food,
            "marriage_allowance": marriage,
            "children_allowance": children,
            "overtime_pay": overtime_pay,
            "gross_pay": gross_pay,
            "insurance_employee": insurance_employee,
            "insurance_employer": insurance_employer,
            "income_tax": tax,
            "other_deductions": other,
            "net_pay": net_pay,
            "taxable_income": taxable,
            "tax_breakdown": breakdown,
        },
    )
    return payslip


@transaction.atomic
def calculate_payroll(payroll_run: PayrollRun, user=None, request=None) -> PayrollRun:
    if payroll_run.status == PayrollRun.Status.POSTED:
        raise ValidationError("این دوره قبلاً ثبت شده است.")

    employees = Employee.objects.filter(
        company=payroll_run.company, is_active=True,
        hire_date__lte=payroll_run.period_end,
    ).exclude(
        termination_date__lt=payroll_run.period_start,
        termination_date__isnull=False,
    )

    payroll_run.payslips.all().delete()

    for emp in employees:
        calculate_payslip(employee=emp, payroll_run=payroll_run)

    payroll_run.recalc_totals()
    payroll_run.status = PayrollRun.Status.CALCULATED
    payroll_run.save(update_fields=["status"])

    log_activity(
        action="update", obj=payroll_run, user=user, request=request,
        description=f"محاسبه‌ی {employees.count()} فیش — جمع خالص: {payroll_run.total_net:,.2f}",
    )
    return payroll_run


@transaction.atomic
def post_payroll(payroll_run: PayrollRun, user=None, request=None):
    """ثبت نهایی دوره: ایجاد سند حسابداری."""
    if payroll_run.status != PayrollRun.Status.CALCULATED:
        raise ValidationError("ابتدا دوره را محاسبه کنید.")
    if not payroll_run.payslips.exists():
        raise ValidationError("هیچ فیش حقوقی محاسبه نشده است.")

    company = payroll_run.company

    salaries = ensure_account(company, "SALARIES_EXPENSE", "5202",
                              "هزینه حقوق و دستمزد", "EXPENSE")
    employer_ins = ensure_account(company, "EMPLOYER_INSURANCE_EXPENSE", "5203",
                                  "هزینه بیمه سهم کارفرما", "EXPENSE")
    ins_payable = ensure_account(company, "INSURANCE_PAYABLE", "2103",
                                 "بیمه تأمین اجتماعی پرداختنی", "LIABILITY")
    tax_payable = ensure_account(company, "TAX_PAYABLE", "2104",
                                 "مالیات بر درآمد حقوق پرداختنی", "LIABILITY")
    bank = ensure_account(company, "BANK", "110102", "بانک", "ASSET")

    journal = Journal.objects.create(
        company=company, fiscal_year=payroll_run.fiscal_year,
        number=f"PAY-{payroll_run.year}{payroll_run.month:02d}",
        date=payroll_run.period_end,
        description=f"حقوق و دستمزد {payroll_run.year}/{payroll_run.month:02d}",
        created_by=user,
    )

    seq = 1
    JournalEntry.objects.create(
        journal=journal, account=salaries, debit=payroll_run.total_gross,
        description="هزینه حقوق و دستمزد", sequence=seq,
    ); seq += 1

    if payroll_run.total_insurance_employer > 0:
        JournalEntry.objects.create(
            journal=journal, account=employer_ins, debit=payroll_run.total_insurance_employer,
            description="بیمه سهم کارفرما", sequence=seq,
        ); seq += 1

    total_ins = payroll_run.total_insurance_employee + payroll_run.total_insurance_employer
    if total_ins > 0:
        JournalEntry.objects.create(
            journal=journal, account=ins_payable, credit=total_ins,
            description="بیمه تأمین اجتماعی پرداختنی", sequence=seq,
        ); seq += 1

    if payroll_run.total_income_tax > 0:
        JournalEntry.objects.create(
            journal=journal, account=tax_payable, credit=payroll_run.total_income_tax,
            description="مالیات بر درآمد حقوق پرداختنی", sequence=seq,
        ); seq += 1

    if payroll_run.total_net > 0:
        JournalEntry.objects.create(
            journal=journal, account=bank, credit=payroll_run.total_net,
            description="پرداخت حقوق به کارمندان", sequence=seq,
        )

    journal.post(user=user)

    payroll_run.journal = journal
    payroll_run.status = PayrollRun.Status.POSTED
    payroll_run.save(update_fields=["journal", "status"])

    log_activity(
        action="post", obj=payroll_run, user=user, request=request,
        changes={"status": "posted", "journal": journal.number},
        description=f"سند حقوق — خالص: {payroll_run.total_net:,.2f}",
    )
    return journal