from django.urls import path
from . import views

app_name = "moadian"
urlpatterns = [
    path("config/", views.ConfigView.as_view(), name="config"),
    path("invoices/", views.InvoiceListView.as_view(), name="invoices"),
    path("send/<str:document_type>/<int:pk>/", views.SendView.as_view(), name="send"),
    path("refresh/<int:pk>/", views.RefreshStatusView.as_view(), name="refresh"),
    path("server-info/", views.ServerInfoView.as_view(), name="server_info"),
    path("economic-inquiry/", views.EconomicCodeInquiryView.as_view(), name="economic_inquiry"),
]
