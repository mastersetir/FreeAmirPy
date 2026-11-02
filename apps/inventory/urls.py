from django.urls import path
from . import views

app_name = "inventory"
urlpatterns = [
    path("warehouses/", views.WarehouseListView.as_view(), name="warehouses"),
    path("warehouses/new/", views.WarehouseCreateView.as_view(), name="warehouse_new"),
    path("moves/", views.StockMoveListView.as_view(), name="moves"),
    path("stock-in/", views.StockInView.as_view(), name="stock_in"),
    path("balances/", views.BalanceListView.as_view(), name="balances"),
]
