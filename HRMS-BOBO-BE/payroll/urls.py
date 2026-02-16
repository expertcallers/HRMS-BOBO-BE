from django.urls import path

from hrms import settings
from payroll import views

urlpatterns = [
    path("get_my_ecpl_employee_payroll", views.GetMyECPLPayroll.as_view()),
]
if not settings.IS_PUBLIC_SERVER:
    urlpatterns += [
        # path("get_all_employee_payroll", views.GetAllPayroll.as_view(), name="get_all_employee_payroll"),
        path("get_all_ecpl_employee_payroll", views.GetAllPayroll.as_view(), name="get_all_ecpl_employee_payroll"),
        path("get_all_deductions", views.GetAllDeductions.as_view(), name="get_all_deductions"),
        path("get_all_variable_pay", views.GetAllVariablePay.as_view(), name="get_all_variable_pay"),
        path("calculate_payroll", views.calculate_payroll, name="calculate_payroll"),
        path("add_deduction", views.add_deduction, name="add_payroll_deduction"),
        path("add_variable_pay", views.add_variable_pay, name="add_variable_pay"),
        path("update_variable_pay/<str:vid>", views.update_variable_pay, name="update_variable_pay_by_id"),
        path("upload_payroll", views.upload_payroll, name="upload_payroll"),
        path("get_salary_structure", views.get_salary_structure, name="get_salary_structure"),
        path("upload_variable_pay", views.upload_variable_pay, name="upload_variable_pay"),
        path("upload_salary", views.upload_salary, name="upload_salary"),
        path("update_salary/<sal_id>", views.update_salary, name="update_salary"),
        path("view_all_salary", views.GetAllSalary.as_view(), name="view_all_salary"),
        path("update_variable_pay_status", views.update_variable_pay_status, name="update_variable_pay_status"),
        path("get_all_variable_pay_to_be_approved", views.GetAllVariablePayToBeApproved.as_view(),
             name="get_all_variable_pay_to_be_approved_mgmt_only"),
        path("variable_pay_approve_count", views.get_variable_pay_approve_count,
             name="variable_pay_approve_count_mgmt_only")
    ]
