from django import forms
from django.forms import inlineformset_factory

from .models import SaleInvoice, SaleInvoiceLine, SaleReturn, SaleReturnLine

class SaleInvoiceForm(forms.ModelForm):
    class Meta:
        model = SaleInvoice
        fields = ("number", "date", "customer", "settlement_method")
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-input"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "customer": forms.Select(attrs={"class": "form-input"}),
            "settlement_method": forms.Select(attrs={"class": "form-input"}),
        }

SaleInvoiceLineFormSet = inlineformset_factory(
    SaleInvoice, SaleInvoiceLine,
    fields=("product", "warehouse", "quantity", "unit_price", "discount", "vat_rate"),
    extra=3, min_num=1, validate_min=True, can_delete=True,
    widgets={
        "product": forms.Select(attrs={"class": "form-input"}),
        "warehouse": forms.Select(attrs={"class": "form-input"}),
        "quantity": forms.NumberInput(attrs={"class": "form-input", "step": "0.001"}),
        "unit_price": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
        "discount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
        "vat_rate": forms.NumberInput(attrs={"class": "form-input"}),
    },
)

class SaleReturnForm(forms.ModelForm):
    class Meta:
        model = SaleReturn
        fields = ("number", "date")
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-input"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        }

SaleReturnLineFormSet = inlineformset_factory(
    SaleReturn, SaleReturnLine,
    fields=("quantity", "discount"),
    extra=0, can_delete=True,
    widgets={
        "quantity": forms.NumberInput(attrs={"class": "form-input", "step": "0.001"}),
        "discount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
    },
)

class InvoicePickerForm(forms.Form):
    invoice = forms.ModelChoiceField(
        queryset=SaleInvoice.objects.none(), label="فاکتور فروش",
        widget=forms.Select(attrs={"class": "form-input"}),
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["invoice"].queryset = (
                SaleInvoice.objects.filter(company=company, status=SaleInvoice.Status.POSTED)
                .select_related("customer").order_by("-date")
            )
