"""ایجاد دفتر حساب‌های پیش‌فرض ایرانی برای یک شرکت."""
from django.core.management.base import BaseCommand

from apps.accounting.models import Account
from apps.core.models import Company

DEFAULT_COA = [
    ("1", "دارایی‌ها", "ASSET", None),
    ("11", "دارایی‌های جاری", "ASSET", "1"),
    ("1101", "موجودی نقد و بانک", "ASSET", "11"),
    ("110101", "صندوق", "ASSET", "1101"),
    ("110102", "بانک", "ASSET", "1101"),
    ("1102", "حساب‌های دریافتنی", "ASSET", "11"),
    ("110201", "حساب‌های دریافتنی تجاری", "ASSET", "1102"),
    ("1103", "موجودی کالا", "ASSET", "11"),
    ("12", "دارایی‌های ثابت", "ASSET", "1"),
    ("1201", "اموال، ماشین‌آلات و تجهیزات", "ASSET", "12"),

    ("2", "بدهی‌ها", "LIABILITY", None),
    ("21", "بدهی‌های جاری", "LIABILITY", "2"),
    ("2101", "حساب‌های پرداختنی تجاری", "LIABILITY", "21"),
    ("2102", "مالیات بر ارزش افزوده پرداختنی", "LIABILITY", "21"),
    ("2103", "بیمه تأمین اجتماعی پرداختنی", "LIABILITY", "21"),
    ("2104", "مالیات بر درآمد حقوق پرداختنی", "LIABILITY", "21"),

    ("3", "سرمایه", "EQUITY", None),
    ("31", "سرمایه", "EQUITY", "3"),
    ("3101", "سرمایه اولیه", "EQUITY", "31"),
    ("3102", "سود و زیان انباشته", "EQUITY", "31"),

    ("4", "درآمدها", "REVENUE", None),
    ("41", "درآمد فروش", "REVENUE", "4"),
    ("4101", "فروش کالا و خدمات", "REVENUE", "41"),

    ("5", "هزینه‌ها", "EXPENSE", None),
    ("51", "بهای تمام شده", "EXPENSE", "5"),
    ("5101", "بهای تمام شده کالای فروش رفته", "EXPENSE", "51"),
    ("52", "هزینه‌های عمومی و اداری", "EXPENSE", "5"),
    ("5201", "هزینه اجاره", "EXPENSE", "52"),
    ("5202", "هزینه حقوق و دستمزد", "EXPENSE", "52"),
    ("5203", "هزینه بیمه سهم کارفرما", "EXPENSE", "52"),
]

class Command(BaseCommand):
    help = "Create the default Iranian chart of accounts for a company."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, required=True)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, company_id, force, **kwargs):
        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            self.stderr.write(f"Company {company_id} not found.")
            return

        if Account.objects.filter(company=company).exists() and not force:
            self.stdout.write(self.style.WARNING("Accounts already exist. Use --force to recreate."))
            return

        by_code = {}
        for code, name, atype, parent in DEFAULT_COA:
            account, _ = Account.objects.update_or_create(
                company=company, code=code,
                defaults={"name": name, "account_type": atype,
                          "parent": by_code.get(parent),
                          "is_postable": not any(c[3] == code for c in DEFAULT_COA)},
            )
            by_code[code] = account

        self.stdout.write(self.style.SUCCESS(f"Chart of accounts created for {company.name}."))
