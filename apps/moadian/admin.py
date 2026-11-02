from django.contrib import admin
from .models import MoadianConfig, MoadianInvoice, MoadianLog

@admin.register(MoadianConfig)
class MoadianConfigAdmin(admin.ModelAdmin):
    list_display = ("company", "tax_id", "environment", "is_active")
    list_filter = ("environment", "is_active")
    fields = ("company", "tax_id", "client_id", "client_secret", "private_key", "environment", "is_active")

@admin.register(MoadianInvoice)
class MoadianInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "document_type", "document_repr", "status",
                    "reference_number", "tax_id", "created_at")
    list_filter = ("status", "document_type", "company")
    search_fields = ("reference_number", "tax_id", "document_repr")
    readonly_fields = ("request_payload", "response_payload", "error_message",
                       "sent_at", "verified_at", "reference_number", "tax_id", "document_repr")

@admin.register(MoadianLog)
class MoadianLogAdmin(admin.ModelAdmin):
    list_display = ("id", "config", "endpoint", "method", "response_status", "created_at")
    list_filter = ("response_status", "method")
    readonly_fields = ("config", "endpoint", "method", "request_body", "response_status",
                       "response_body", "created_at")
