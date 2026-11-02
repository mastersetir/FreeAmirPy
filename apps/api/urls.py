from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("accounts", views.AccountViewSet, basename="account")
router.register("journals", views.JournalViewSet, basename="journal")

reports = views.ReportViewSet.as_view({"get": "trial_balance"})
ledger_view = views.ReportViewSet.as_view({"get": "ledger"})

urlpatterns = [
    path("", include(router.urls)),
    path("reports/trial-balance/", reports, name="api-trial-balance"),
    path("reports/ledger/", ledger_view, name="api-ledger"),
]
