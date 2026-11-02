from django.contrib import admin
from .models import Customer, Product, SaleInvoice, SaleInvoiceLine, SaleReturn, SaleReturnLine

class SaleInvoiceLineInline(admin.TabularInline):
    model = SaleInvoiceLine
    extra = 1

class SaleReturnLineInline(admin.TabularInline):
    model = SaleReturnLine
    extra = 0
    readonly_fields = ("product", "original_line", "unit_price", "unit_cogs")

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "national_id", "customer_type", "company")
    list_filter = ("company", "customer_type")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "unit_price", "vat_rate", "company")
    list_filter = ("company",)

@admin.register(SaleInvoice)
class SaleInvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "customer", "status", "total_amount", "company")
    list_filter = ("company", "status")
    inlines = [SaleInvoiceLineInline]

@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "invoice", "status", "total_amount", "company")
    list_filter = ("company", "status")
    inlines = [SaleReturnLineInline]
