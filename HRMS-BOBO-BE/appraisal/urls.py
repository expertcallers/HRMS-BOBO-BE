from django.urls import path
from appraisal import views

urlpatterns = [
    path("add_parta_parameter", views.add_parta_parameter, name="add_parta_parameter"),
    path("get_parameter_name", views.get_parameter_name),
    path("all_appraisal_eligible_employees_list", views.GetAllEligibleAppraisalEmployeesList.as_view(),
         name="all_appraisal_eligible_employees_list"),
    path("all_appraisal_eligible_employees_list_mgmt", views.GetAllEligibleAppraisalEmployeesList.as_view(),
         name="all_appraisal_eligible_employees_list_mgmt"),
    path("get_designation_mapping", views.get_designation_mapping),
    path("get_employees_tobe_added", views.get_employees_tobe_added),
    path("get_default_params/<str:desi_map_name>", views.get_default_params),
    path("get_self_appraisal_status", views.get_self_appraisal_status),
    path("get_mgr_appraisal_status/<str:appraisal_id>", views.get_mgr_appraisal_status,
         name="get_mgr_appraisal_status"),
    path("get_self_appraisal_parameters/<str:param_type>", views.get_self_appraisal_parameters),
    path("get_mgr_appraisal_parameters/<str:appraisal_id>", views.get_mgr_appraisal_parameters,
         name="get_mgr_appraisal_parameters"),
    path("add_self_appraisal/<str:param_type>", views.add_self_appraisal),
    path("add_mgr_appraisal/<str:appraisal_id>", views.add_mgr_apprisal, name="add_mgr_appraisal"),
    path("get_all_emp_appraisals", views.GetAllAppraisal.as_view(), name="get_all_emp_appraisals"),
    path("get_all_emp_appraisals_mgmt", views.GetAllAppraisal.as_view(), name="get_all_emp_appraisals_mgmt"),
    path("get_all_emp_parameters/<str:appraisal_id>", views.get_all_emp_parameters),
    path("add_appraisee_partd", views.add_appraisee_partd),
    path("get_appraisal_stats", views.get_appraisal_stats, name="get_appraisal_stats"),
    path("get_appraisal_report", views.get_appraisal_report, name="get_appraisal_report"),
    path("get_overall_appraisal_stats", views.get_overall_appraisal_stats, name="get_overall_appraisal_stats")
]
