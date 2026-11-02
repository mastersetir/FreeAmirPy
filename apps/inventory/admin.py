from django.contrib import admin
from .models import StockBalance, StockMove, Warehouse

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "is_active")
    list_filter = ("company", "is_active")

@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
    list_display = ("date", "warehouse", "product", "move_type", "quantity", "unit_cost", "total_cost")
    list_filter = ("move_type", "warehouse")
    search_fields = ("reference", "product__name", "product__code")
    readonly_fields = ("unit_cost", "total_cost")

@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "product", "quantity", "avg_cost", "total_value")
    list_filter = ("warehouse",)
    readonly_fields = ("avg_cost", "total_value")
