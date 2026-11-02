from django.urls import path
from . import views

app_name = "accounting"
urlpatterns = [
    path("accounts/", views.AccountListView.as_view(), name="accounts"),
    path("accounts/new/", views.AccountCreateView.as_view(), name="account_new"),
    path("accounts/<int:pk>/edit/", views.AccountEditView.as_view(), name="account_edit"),

    path("journals/", views.JournalListView.as_view(), name="journals"),
    path("journals/new/", views.JournalCreateView.as_view(), name="journal_new"),
    path("journals/<int:pk>/", views.JournalDetailView.as_view(), name="journal_detail"),
    path("journals/<int:pk>/edit/", views.JournalEditView.as_view(), name="journal_edit"),
    path("journals/<int:pk>/post/", views.JournalPostView.as_view(), name="journal_post"),

    path("reports/trial-balance/", views.TrialBalanceView.as_view(), name="trial_balance"),
    path("reports/ledger/", views.LedgerView.as_view(), name="ledger"),
    path("reports/balance-sheet/", views.BalanceSheetView.as_view(), name="balance_sheet"),
    path("reports/income-statement/", views.IncomeStatementView.as_view(), name="income_statement"),

    path("close-fiscal-year/", views.CloseFiscalYearView.as_view(), name="close_fiscal_year"),
]
