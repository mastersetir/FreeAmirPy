from django import forms
from django.forms import inlineformset_factory

from .models import PurchaseInvoice, PurchaseInvoiceLine, PurchaseReturn, PurchaseReturnLine

class PurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoice
        fields = ("number", "date", "supplier")
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-input"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "supplier": forms.Select(attrs={"class": "form-input"}),
        }

PurchaseInvoiceLineFormSet = inlineformset_factory(
    PurchaseInvoice, PurchaseInvoiceLine,
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

class PurchaseReturnForm(forms.ModelForm):
    class Meta:
        model = PurchaseReturn
        fields = ("number", "date")
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-input"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        }

PurchaseReturnLineFormSet = inlineformset_factory(
    PurchaseReturn, PurchaseReturnLine,
    fields=("quantity", "discount"),
    extra=0, can_delete=True,
    widgets={
        "quantity": forms.NumberInput(attrs={"class": "form-input", "step": "0.001"}),
        "discount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
    },
)

class PurchaseInvoicePickerForm(forms.Form):
    invoice = forms.ModelChoiceField(
        queryset=PurchaseInvoice.objects.none(), label="فاکتور خرید",
        widget=forms.Select(attrs={"class": "form-input"}),
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["invoice"].queryset = (
                PurchaseInvoice.objects.filter(company=company, status=PurchaseInvoice.Status.POSTED)
                .select_related("supplier").order_by("-date")
            )
