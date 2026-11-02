from django import forms
from .models import Warehouse

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ("code", "name", "address", "is_active")
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "address": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }

class StockInForm(forms.Form):
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.none(), label="انبار",
                                       widget=forms.Select(attrs={"class": "form-input"}))
    product = forms.ModelChoiceField(queryset=None, label="کالا",
                                     widget=forms.Select(attrs={"class": "form-input"}))
    quantity = forms.DecimalField(label="مقدار", min_value=0.001, decimal_places=3,
                                  widget=forms.NumberInput(attrs={"class": "form-input", "step": "0.001"}))
    unit_cost = forms.DecimalField(label="بهای واحد", min_value=0, decimal_places=2,
                                   widget=forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}))
    date = forms.DateField(label="تاریخ", widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}))
    reference = forms.CharField(label="مرجع (اختیاری)", required=False, max_length=100,
                                widget=forms.TextInput(attrs={"class": "form-input"}))
    note = forms.CharField(label="توضیحات", required=False,
                           widget=forms.Textarea(attrs={"class": "form-input", "rows": 2}))

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            from apps.sales.models import Product
            self.fields["warehouse"].queryset = Warehouse.objects.filter(company=company, is_active=True)
            self.fields["product"].queryset = Product.objects.filter(company=company).order_by("code")
