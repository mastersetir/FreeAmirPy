from django.urls import path
from django.views.generic import TemplateView
from apps.core import approval_views, views

app_name = "core"
urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("activity/", views.ActivityLogView.as_view(), name="activity"),
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),

    path("approvals/", approval_views.ApprovalListView.as_view(), name="approvals"),
    path("approvals/request/<str:model_name>/<int:pk>/",
         approval_views.RequestApprovalView.as_view(), name="approval_request"),
    path("approvals/<int:pk>/<str:action>/",
         approval_views.ReviewApprovalView.as_view(), name="approval_review"),

    path("switch-company/<int:company_id>/", views.switch_company, name="switch_company"),
    path("switch-fiscal-year/<int:fy_id>/", views.switch_fiscal_year, name="switch_fiscal_year"),
]
