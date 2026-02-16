from django.urls import path

from hrms import settings
from mapping import views

# TODO add impacted my_teams fields while mapping a team
urlpatterns = [
    path('reset_password', views.reset_user_password),
    path('login', views.LoginUserView.as_view()),
    path('logout', views.Logout.as_view()),
    path('remove_prof_image', views.remove_profile_image),
    path('user_image', views.user_image),
    path("get_pre_defined", views.get_pre_defined),
    path("get_user_permissions", views.get_user_permissions),
    path("send_email_otp_forgot_password", views.send_email_otp_forgot_password),
    path("create_exception_log", views.create_exception_log),
    path("forgot_password", views.forgot_password),
    path("update_initial_password", views.update_initial_password),
    path("frontend_version", views.frontend_version),
    path("get_all_open_referrals", views.get_all_open_referrals),
    path("get_process_designations_by_dept", views.get_designations_by_dept),
    path("send_login_email_otp", views.send_login_email_otp)

]
if not settings.IS_PUBLIC_SERVER:
    urlpatterns += [
        path("remove_permissions", views.remove_permissions, name="remove_permissions_cc_team_only"),
        path("create_employee/<str:ob_id>", views.create_employee, name="create_new_employee"),
        path("get_d/<str:id_val>/<str:name>", views.get_id_value, name="decrypt_id"),
        path("get_birthdays", views.get_birthdays),
        path("get_new_hires", views.get_new_hires),
        path("create_emp_ref", views.create_employee_reference),
        path("create_emp_ref_by_ta/<str:emp_id>", views.create_emp_ref_by_ta, name="create_emp_ref_by_ta"),
        path("get_all_employee_referral", views.GetAllEmployeeReferences.as_view(), name="get_all_employee_referral"),
        path("get_open_employee_ref_count", views.get_open_employee_ref_count, name="get_open_employee_ref_count"),
        path("update_emp_referral_status/<str:emp_ref_id>", views.update_emp_ref_status,
             name="update_emp_referral_status"),
        path("get_my_employee_referrals", views.GetMyEmployeeReferences.as_view()),
        path("get_my_team_referrals", views.GetMyTeamReferences.as_view(), name="get_my_team_referrals"),
        path("create_process", views.create_process, name="create_process"),
        path("create_designation", views.create_designation, name="create_designation"),
        path("create_mapping", views.create_mapping, name="create_mapping"),
        path("get_my_team_mapping", views.GetMyTeamMappingRequests.as_view(), name="get_my_team_mapping"),
        path("get_my_team_mapping_count", views.get_my_team_mapping_request_count, name="get_my_team_mapping_count"),
        path("get_my_team_mapping_history", views.GetMyTeamHistoryMapping.as_view(),
             name="get_my_team_mapping_history"),
        path("get_all_team_mapping", views.GetAllTeamMapping.as_view(), name="get_all_team_mapping"),
        path("approve_mapping/<str:mapping_id>", views.approve_mapping, name="approve_mapping"),
        path("update_employee/<str:emp_id>", views.update_employee, name="update_employee_info"),
        path("reset_password_by_mgr/<str:emp_id>", views.reset_password_by_mgr, name="reset_password_by_mgr"),
        path("get_all_profiles_for_pbi", views.get_all_profiles_for_pbi),
        path("clear_mfa_passkeys", views.clear_mfa_passkeys, name="clear_mfa_passkeys_ccteam_only")
        # TODO add assign manager to team
    ]
