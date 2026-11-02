from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.activity import log_activity
from apps.core.utils import get_active_company, get_active_fiscal_year

from .closing import close_fiscal_year, preview_close
from .forms import AccountForm, JournalEntryFormSet, JournalForm
from .models import Account, Journal
from .reports import balance_sheet, income_statement
from .services import ledger as build_ledger, trial_balance

class ScopedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.company = get_active_company(request)
        self.fiscal_year = get_active_fiscal_year(request)
        if not self.company:
            messages.error(request, "هیچ شرکت فعالی وجود ندارد. ابتدا از ادمین یک شرکت بسازید.")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

class AccountListView(ScopedMixin, ListView):
    model = Account
    template_name = "accounting/account_list.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return Account.objects.filter(company=self.company).order_by("code")

class AccountCreateView(ScopedMixin, View):
    template_name = "accounting/account_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": AccountForm(), "title": "حساب جدید"})

    def post(self, request):
        form = AccountForm(request.POST)
        if form.is_valid():
            acc = form.save(commit=False)
            acc.company = self.company
            acc.save()
            log_activity(action="create", obj=acc, request=request)
            messages.success(request, "حساب ایجاد شد.")
            return redirect("accounting:accounts")
        return render(request, self.template_name, {"form": form, "title": "حساب جدید"})

class AccountEditView(ScopedMixin, View):
    template_name = "accounting/account_form.html"

    def get(self, request, pk):
        acc = get_object_or_404(Account, pk=pk, company=self.company)
        return render(request, self.template_name,
                      {"form": AccountForm(instance=acc), "title": f"ویرایش حساب {acc.code}"})

    def post(self, request, pk):
        acc = get_object_or_404(Account, pk=pk, company=self.company)
        form = AccountForm(request.POST, instance=acc)
        if form.is_valid():
            form.save()
            log_activity(action="update", obj=acc, request=request)
            messages.success(request, "حساب ویرایش شد.")
            return redirect("accounting:accounts")
        return render(request, self.template_name, {"form": form, "title": f"ویرایش {acc.code}"})

class JournalListView(ScopedMixin, ListView):
    model = Journal
    template_name = "accounting/journal_list.html"
    context_object_name = "journals"
    paginate_by = 30

    def get_queryset(self):
        qs = Journal.objects.filter(company=self.company).select_related("fiscal_year")
        if self.fiscal_year:
            qs = qs.filter(fiscal_year=self.fiscal_year)
        return qs

class JournalCreateView(ScopedMixin, View):
    template_name = "accounting/journal_form.html"

    def get(self, request):
        form = JournalForm(initial={"number": self._next_number()})
        formset = JournalEntryFormSet()
        self._limit_accounts(formset)
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request):
        form = JournalForm(request.POST)
        formset = JournalEntryFormSet(request.POST)
        self._limit_accounts(formset)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                journal = form.save(commit=False)
                journal.company = self.company
                journal.fiscal_year = self.fiscal_year
                journal.created_by = request.user
                journal.save()
                formset.instance = journal
                formset.save()
            log_activity(action="create", obj=journal, request=request)
            messages.success(request, "سند ایجاد شد. برای نهایی‌سازی دکمه‌ی ثبت را بزنید.")
            return redirect("accounting:journal_detail", pk=journal.pk)
        return render(request, self.template_name, {"form": form, "formset": formset})

    def _next_number(self):
        if not self.fiscal_year:
            return ""
        last = Journal.objects.filter(fiscal_year=self.fiscal_year).order_by("-id").first()
        try:
            n = int(last.number) if last else 0
        except (ValueError, TypeError):
            n = 0
        return f"{n + 1:05d}"

    def _limit_accounts(self, formset):
        if self.company:
            postable = Account.objects.filter(company=self.company, is_postable=True, is_active=True)
            for f in formset.forms:
                f.fields["account"].queryset = postable

class JournalEditView(ScopedMixin, View):
    template_name = "accounting/journal_form.html"

    def get(self, request, pk):
        journal = get_object_or_404(Journal, pk=pk, company=self.company)
        if journal.is_posted:
            messages.error(request, "سند ثبت‌شده قابل ویرایش نیست.")
            return redirect("accounting:journal_detail", pk=pk)
        form = JournalForm(instance=journal)
        formset = JournalEntryFormSet(instance=journal)
        self._limit_accounts(formset)
        return render(request, self.template_name, {"form": form, "formset": formset, "journal": journal})

    def post(self, request, pk):
        journal = get_object_or_404(Journal, pk=pk, company=self.company)
        if journal.is_posted:
            messages.error(request, "سند ثبت‌شده قابل ویرایش نیست.")
            return redirect("accounting:journal_detail", pk=pk)
        form = JournalForm(request.POST, instance=journal)
        formset = JournalEntryFormSet(request.POST, instance=journal)
        self._limit_accounts(formset)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            log_activity(action="update", obj=journal, request=request)
            messages.success(request, "سند ویرایش شد.")
            return redirect("accounting:journal_detail", pk=pk)
        return render(request, self.template_name, {"form": form, "formset": formset, "journal": journal})

    def _limit_accounts(self, formset):
        postable = Account.objects.filter(company=self.company, is_postable=True, is_active=True)
        for f in formset.forms:
            f.fields["account"].queryset = postable

class JournalDetailView(ScopedMixin, View):
    template_name = "accounting/journal_detail.html"

    def get(self, request, pk):
        journal = get_object_or_404(
            Journal.objects.select_related("fiscal_year").prefetch_related("entries__account"),
            pk=pk, company=self.company,
        )
        return render(request, self.template_name, {"journal": journal})

class JournalPostView(ScopedMixin, View):
    def post(self, request, pk):
        journal = get_object_or_404(Journal, pk=pk, company=self.company)
        try:
            journal.post(user=request.user)
            log_activity(action="post", obj=journal, request=request,
                         changes={"status": "posted"},
                         description=f"جمع: {journal.total_debit:,.2f}")
            messages.success(request, "سند با موفقیت ثبت شد.")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا در ثبت سند: {exc}")
        return redirect("accounting:journal_detail", pk=pk)

class TrialBalanceView(ScopedMixin, View):
    template_name = "accounting/trial_balance.html"

    def get(self, request):
        if not self.fiscal_year:
            messages.warning(request, "سال مالی فعالی وجود ندارد.")
            return redirect("core:dashboard")
        rows, total_d, total_c = trial_balance(self.fiscal_year)
        return render(request, self.template_name, {
            "rows": rows, "total_debit": total_d, "total_credit": total_c,
            "balanced": total_d == total_c,
        })

class LedgerView(ScopedMixin, View):
    template_name = "accounting/ledger.html"

    def get(self, request):
        if not self.fiscal_year:
            messages.warning(request, "سال مالی فعالی وجود ندارد.")
            return redirect("core:dashboard")
        accounts = Account.objects.filter(company=self.company, is_postable=True).order_by("code")
        account_id = request.GET.get("account")
        account, rows, balance = None, [], 0
        if account_id:
            account = get_object_or_404(Account, pk=account_id, company=self.company)
            rows, balance = build_ledger(self.fiscal_year, account)
        return render(request, self.template_name, {
            "accounts": accounts, "account": account, "rows": rows, "balance": balance,
        })

class BalanceSheetView(ScopedMixin, View):
    template_name = "accounting/balance_sheet.html"

    def get(self, request):
        as_of_str = request.GET.get("as_of")
        if as_of_str:
            try:
                as_of = date.fromisoformat(as_of_str)
            except ValueError:
                as_of = date.today()
        else:
            as_of = date.today()
            if self.fiscal_year and self.fiscal_year.end_date < as_of:
                as_of = self.fiscal_year.end_date
        return render(request, self.template_name, balance_sheet(self.company, as_of))

class IncomeStatementView(ScopedMixin, View):
    template_name = "accounting/income_statement.html"

    def get(self, request):
        if not self.fiscal_year:
            messages.warning(request, "سال مالی فعالی وجود ندارد.")
            return redirect("core:dashboard")
        return render(request, self.template_name, income_statement(self.fiscal_year))

class CloseFiscalYearView(ScopedMixin, View):
    template_name = "accounting/close_fiscal_year.html"

    def get(self, request):
        if not self.fiscal_year:
            messages.error(request, "سال مالی فعالی وجود ندارد.")
            return redirect("core:dashboard")
        if self.fiscal_year.is_closed:
            messages.info(request, "این سال مالی قبلاً بسته شده است.")
            return redirect("accounting:journals")
        data = preview_close(self.fiscal_year)
        return render(request, self.template_name, {"fiscal_year": self.fiscal_year, **data})

    def post(self, request):
        if not self.fiscal_year:
            return redirect("core:dashboard")
        try:
            journal = close_fiscal_year(self.fiscal_year, user=request.user, request=request)
            if journal:
                messages.success(request, f"سال مالی بسته شد. سند بستن: {journal.number}")
            else:
                messages.success(request, "سال مالی بسته شد (بدون جنبش درآمد/هزینه).")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"خطا: {exc}")
        return redirect("accounting:journals")
