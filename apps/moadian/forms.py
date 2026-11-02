from django import forms
from .models import MoadianConfig

class MoadianConfigForm(forms.ModelForm):
    class Meta:
        model = MoadianConfig
        fields = ("tax_id", "client_id", "client_secret", "private_key", "environment", "is_active")
        widgets = {
            "tax_id": forms.TextInput(attrs={"class": "form-input"}),
            "client_id": forms.TextInput(attrs={"class": "form-input"}),
            "client_secret": forms.TextInput(attrs={"class": "form-input"}),
            "private_key": forms.Textarea(attrs={"class": "form-input", "rows": 8}),
            "environment": forms.Select(attrs={"class": "form-input"}),
        }

class EconomicCodeInquiryForm(forms.Form):
    economic_code = forms.CharField(label="کد اقتصادی", max_length=20,
                                    widget=forms.TextInput(attrs={"class": "form-input"}))
