from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounting.models import Account, Journal
from apps.accounting.services import trial_balance, ledger
from apps.core.utils import get_active_company, get_active_fiscal_year

from .serializers import AccountSerializer, JournalSerializer

class CompanyScopedViewSet(viewsets.ModelViewSet):
    def get_company(self):
        return get_active_company(self.request)

    def get_queryset(self):
        company = self.get_company()
        if not company:
            return self.queryset.none()
        return self.queryset.filter(company=company)

class AccountViewSet(CompanyScopedViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

class JournalViewSet(CompanyScopedViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer

    @action(detail=True, methods=["post"])
    def post_journal(self, request, pk=None):
        journal = self.get_object()
        try:
            journal.post(user=request.user)
            return Response({"status": "posted"})
        except Exception as exc:  # noqa: BLE001
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

class ReportViewSet(viewsets.ViewSet):
    def trial_balance(self, request):
        fy = get_active_fiscal_year(request)
        if not fy:
            return Response({"error": "no active fiscal year"}, status=400)
        rows, d, c = trial_balance(fy)
        return Response({"rows": rows, "total_debit": str(d), "total_credit": str(c)})

    def ledger(self, request):
        fy = get_active_fiscal_year(request)
        account_id = request.query_params.get("account")
        if not fy or not account_id:
            return Response({"error": "fiscal year and account required"}, status=400)
        account = Account.objects.get(pk=account_id, company=get_active_company(request))
        rows, bal = ledger(fy, account)
        return Response({"account": AccountSerializer(account).data,
                         "rows": rows, "balance": str(bal)})
