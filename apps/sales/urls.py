from django.urls import path
from . import views

app_name = "sales"
urlpatterns = [
    path("invoices/", views.InvoiceListView.as_view(), name="invoices"),
    path("invoices/new/", views.InvoiceCreateView.as_view(), name="invoice_new"),
    path("invoices/<int:pk>/post/", views.InvoicePostView.as_view(), name="invoice_post"),

    path("returns/", views.ReturnListView.as_view(), name="returns"),
    path("returns/new/", views.ReturnPickerView.as_view(), name="return_new"),
    path("returns/<int:pk>/edit/", views.ReturnEditView.as_view(), name="return_edit"),
    path("returns/<int:pk>/post/", views.ReturnPostView.as_view(), name="return_post"),
]
