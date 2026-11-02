from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import CompanyAccess, User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = DjangoUserAdmin.fieldsets + (("FreeAmir", {"fields": ("role", "phone")}),)

@admin.register(CompanyAccess)
class CompanyAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role")
    list_filter = ("company", "role")
