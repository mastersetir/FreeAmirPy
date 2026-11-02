from django.contrib import admin
from .activity import ActivityLog
from .approval import ApprovalRequest
from .models import Company, FiscalYear

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "national_id", "economic_code", "approval_policy", "is_active")
    search_fields = ("name", "national_id")

@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("company", "name", "start_date", "end_date", "is_closed")
    list_filter = ("company", "is_closed")

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "company", "action", "entity", "entity_repr", "ip_address")
    list_filter = ("action", "entity", "company", "user")
    search_fields = ("entity_repr", "description", "user__username")
    readonly_fields = ("user", "company", "action", "entity", "entity_id", "entity_repr",
                       "description", "changes", "ip_address", "user_agent", "created_at")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "content_type", "object_id", "company", "requested_by",
                    "status", "reviewed_by", "requested_at")
    list_filter = ("status", "content_type", "company")
    readonly_fields = ("content_type", "object_id", "company", "requested_by",
                       "requested_at", "reviewed_by", "reviewed_at")
