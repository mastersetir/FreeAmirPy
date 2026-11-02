from django.contrib import admin
from .models import Account, Journal, JournalEntry

class JournalEntryInline(admin.TabularInline):
    model = JournalEntry
    extra = 2
    fields = ("sequence", "account", "debit", "credit", "description")

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "company", "is_postable", "is_active")
    list_filter = ("company", "account_type", "is_postable", "is_active")
    search_fields = ("code", "name")

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "company", "fiscal_year", "is_posted")
    list_filter = ("company", "fiscal_year", "is_posted")
    search_fields = ("number", "description")
    inlines = [JournalEntryInline]
    readonly_fields = ("posted_at", "posted_by")
