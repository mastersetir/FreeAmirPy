from django.contrib import admin
from .models import PurchaseInvoice, PurchaseInvoiceLine, PurchaseReturn, PurchaseReturnLine, Supplier

class PurchaseInvoiceLineInline(admin.TabularInline):
    model = PurchaseInvoiceLine
    extra = 1

class PurchaseReturnLineInline(admin.TabularInline):
    model = PurchaseReturnLine
    extra = 0
    readonly_fields = ("product", "original_line", "unit_price")

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "national_id", "supplier_type", "company")
    list_filter = ("company", "supplier_type")

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "supplier", "status", "total_amount", "company")
    list_filter = ("company", "status")
    inlines = [PurchaseInvoiceLineInline]

@admin.register(PurchaseReturn)
class PurchaseReturnAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "invoice", "status", "total_amount", "company")
    list_filter = ("company", "status")
    inlines = [PurchaseReturnLineInline]
