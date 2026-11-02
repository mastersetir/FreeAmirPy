from rest_framework import serializers
from apps.accounting.models import Account, Journal, JournalEntry

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("id", "code", "name", "account_type", "is_postable", "is_active")

class JournalEntrySerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalEntry
        fields = ("id", "account", "account_code", "account_name",
                  "debit", "credit", "description", "sequence")

class JournalSerializer(serializers.ModelSerializer):
    entries = JournalEntrySerializer(many=True, read_only=True)
    total_debit = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = Journal
        fields = ("id", "number", "date", "description", "is_posted",
                  "total_debit", "total_credit", "entries")
