from django.urls import path
from . import views

app_name = "hr"
urlpatterns = [
    path("employees/", views.EmployeeListView.as_view(), name="employees"),
    path("employees/new/", views.EmployeeCreateView.as_view(), name="employee_new"),
    path("employees/<int:pk>/edit/", views.EmployeeEditView.as_view(), name="employee_edit"),

    path("attendance/", views.AttendanceListView.as_view(), name="attendance"),
    path("attendance/new/", views.AttendanceCreateView.as_view(), name="attendance_new"),

    # ترتیب مهم: config/new باید قبل از <int:pk> بیایند
    path("payrolls/config/", views.PayrollConfigView.as_view(), name="payroll_config"),
    path("payrolls/", views.PayrollListView.as_view(), name="payrolls"),
    path("payrolls/new/", views.PayrollCreateView.as_view(), name="payroll_new"),
    path("payrolls/<int:pk>/", views.PayrollDetailView.as_view(), name="payroll_detail"),
    path("payrolls/<int:pk>/calculate/", views.PayrollCalculateView.as_view(), name="payroll_calculate"),
    path("payrolls/<int:pk>/post/", views.PayrollPostView.as_view(), name="payroll_post"),
]