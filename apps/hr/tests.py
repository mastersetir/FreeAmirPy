from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounting.models import Account
from apps.core.models import Company, FiscalYear

from .models import Attendance, Employee, PayrollRun, TaxBracket
from .services import calculate_income_tax, calculate_payroll, calculate_payslip, get_tax_brackets, post_payroll

def seed_brackets(year=1403):
    for order, mn, mx, rate in [
        (1, Decimal("0"),        Decimal("12000000"),  Decimal("0")),
        (2, Decimal("12000000"), Decimal("16500000"),  Decimal("10")),
        (3, Decimal("16500000"), Decimal("27000000"),  Decimal("15")),
        (4, Decimal("27000000"), Decimal("36000000"),  Decimal("20")),
        (5, Decimal("36000000"), None,                 Decimal("30")),
    ]:
        TaxBracket.objects.create(year=year, order=order, min_amount=mn, max_amount=mx, rate=rate)

class TaxCalculationTests(TestCase):
    def setUp(self):
        seed_brackets(1403)

    def test_below_exemption_is_zero(self):
        brackets = get_tax_brackets(1403)
        tax, _ = calculate_income_tax(Decimal("10000000"), brackets)
        self.assertEqual(tax, Decimal("0"))

    def test_partial_first_bracket(self):
        brackets = get_tax_brackets(1403)
        tax, _ = calculate_income_tax(Decimal("2000000"), brackets)
        self.assertEqual(tax, Decimal("97500.00"))

    def test_top_bracket(self):
        brackets = get_tax_brackets(1403)
        tax, _ = calculate_income_tax(Decimal("40000000"), brackets)
        self.assertEqual(tax, Decimal("4620000.00"))

class PayslipCalculationTests(TestCase):
    def setUp(self):
        seed_brackets(1403)
        self.company = Company.objects.create(name="Test", national_id="12345678901")
        self.fy = FiscalYear.objects.create(
            company=self.company, name="1403",
            start_date=date(2024, 3, 20), end_date=date(2025, 3, 20),
        )
        self.employee = Employee.objects.create(
            company=self.company, code="E001", first_name="علی", last_name="رضایی",
            national_id="0012345678", hire_date=date(2024, 1, 1),
            base_salary=Decimal("20000000"),
            housing_allowance=Decimal("900000"),
            food_allowance=Decimal("1400000"),
        )
        self.payroll = PayrollRun.objects.create(
            company=self.company, fiscal_year=self.fy,
            year=1403, month=6,
            period_start=date(2024, 8, 22), period_end=date(2024, 9, 21),
        )

    def test_simple_payslip(self):
        slip = calculate_payslip(employee=self.employee, payroll_run=self.payroll)
        self.assertEqual(slip.gross_pay, Decimal("22300000.00"))
        self.assertEqual(slip.insurance_employee, Decimal("1561000.00"))
        self.assertEqual(slip.income_tax, Decimal("1858350.00"))
        self.assertEqual(slip.net_pay, Decimal("18880650.00"))

    def test_with_overtime(self):
        Attendance.objects.create(
            company=self.company, employee=self.employee,
            date=date(2024, 9, 1), leave_type=Attendance.LeaveType.PRESENT,
            worked_hours=Decimal("8"), overtime_hours=Decimal("10"),
        )
        slip = calculate_payslip(employee=self.employee, payroll_run=self.payroll)
        expected_ot = (Decimal("20000000") / Decimal("220") * Decimal("1.4") * Decimal("10")).quantize(Decimal("0.01"))
        self.assertEqual(slip.overtime_pay, expected_ot)

    def test_full_payroll_with_journal(self):
        for code, name, atype in [
            ("5202", "حقوق", "EXPENSE"), ("5203", "بیمه کارفرما", "EXPENSE"),
            ("2103", "بیمه پرداختنی", "LIABILITY"), ("2104", "مالیات پرداختنی", "LIABILITY"),
            ("110102", "بانک", "ASSET"),
        ]:
            Account.objects.create(company=self.company, code=code, name=name, account_type=atype)

        calculate_payroll(self.payroll)
        self.assertEqual(self.payroll.payslips.count(), 1)

        journal = post_payroll(self.payroll)
        self.assertTrue(journal.is_posted)
        self.assertEqual(journal.total_debit, journal.total_credit)
