from django import forms
from django.forms import inlineformset_factory

from .models import Account, Journal, JournalEntry

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("code", "name", "account_type", "parent", "is_active")
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "account_type": forms.Select(attrs={"class": "form-input"}),
            "parent": forms.Select(attrs={"class": "form-input"}),
        }

class JournalForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ("number", "date", "description")
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-input"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

JournalEntryFormSet = inlineformset_factory(
    Journal, JournalEntry,
    fields=("account", "debit", "credit", "description"),
    extra=2, min_num=2, validate_min=True, can_delete=True,
    widgets={
        "account": forms.Select(attrs={"class": "form-input"}),
        "debit": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
        "credit": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
        "description": forms.TextInput(attrs={"class": "form-input"}),
    },
)
