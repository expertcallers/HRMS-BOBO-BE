from django.urls import path
from ams import views
from hrms import settings
from .views import BulkAttendanceRangeUpdateView

#  TODO create Download record with processing record and once the file is processed in the backend
#  update the record to the frontend to download the file
urlpatterns = [
    path('apply_for_leave', views.apply_for_leave),
    path('get_team_self_leave_history', views.GetAllTeamSelfLeaveHistory.as_view()),
    path('get_all_leave_history', views.GetAllLeaveHistory.as_view(), name="get_all_leave_history"),
    path('get_my_schedule', views.GetMyAttendanceSchedule.as_view()),
    path('get_all_applied_leaves/<str:eom>', views.GetAllAppliedLeaves.as_view(), name="get_all_applied_leaves"),
    path('appeal_leave_request/<str:leave_id>', views.appeal_leave_request),
    path('get_all_applied_leaves_count/<str:eom>', views.get_all_applied_leaves_count,
         name="get_all_applied_leaves_count"),
    path('get_leave_balance', views.get_leave_balance),
    path('get_my_leave_balance_history', views.GetMyLeaveBalanceHistory.as_view()),
    path('get_team_members_emp_ids', views.get_team_members_emp_ids, name="get_team_members_emp_ids"),
    path('withdraw_leave/<str:leave_id>', views.withdraw_leave),
    path('get_attendance/<str:emp_id>', views.get_attendance),
]
if not settings.IS_PUBLIC_SERVER:
    urlpatterns += [
        path('approve_team_attendance', views.approve_team_attendance, name="approve_team_attendance"),
        path('get_team_schedule', views.GetTeamAttendanceSchedule.as_view(), name="get_team_schedule"),
        path('get_team_approval_schedule/<str:eom>', views.GetApproveTeamAttendanceSchedule.as_view(),
             name="get_team_approval_schedule"),
        path('approve_leave/<str:leave_id>', views.approve_leave, name="approve_the_pending_leaves"),
        path('get_all_unmarked_attendance_count/<str:eom>', views.get_all_unmarked_attendance_count,
             name="get_all_unmarked_attendance_count"),
        path('get_all_leave_balance_history', views.GetAllLeaveBalanceHistory.as_view(),
             name="mgmt_get_all_leave_balance_report"),
        path('update_ml/<str:emp_id>', views.update_ml, name="update_maternity_leave"),
        path("cr_up_schedule", views.create_attend_schedule, name="create_update_schedule"),
        path("upload_attend_schedule", views.upload_attend_schedule, name="upload_attend_schedule"),
        path("upload_attendance", views.upload_attendance, name="upload_attendance"),
        path("update_login_attendance", views.update_login_attendance),
        path("update_logout_attendance", views.update_logout_attendance),
        path("get_attend_login_status", views.get_attend_login_status),
        path("download_all_att_report", views.download_all_att_report, name="download_all_attendance_report"),
        path("download_team_att_report", views.download_team_att_report, name="download_team_attendance_report"),
        path("req_for_att_cor", views.request_for_attendance_correction, name="request_for_attendance_correction"),
        path("get_all_att_cor_req/<str:eom>", views.GetAllAttCorRequests.as_view(),
             name="get_all_attendance_correction_requests"),
        path('get_all_attendance_correction_count/<str:eom>', views.get_all_attendance_correction_count),
        path("approve_cor_req", views.approve_correction_request, name="approve_correction_request"),
        path("schedule_correction", views.schedule_correction, name="schedule_correction"),
        path('get_team_leave_balance', views.GetMyTeamLeaveBalance.as_view(), name="get_team_leave_balance"),

        path("attend_cor_req_history", views.GetAllAttCorReqHistory.as_view(),
             name="attendance_correction_requests_history"),
        path("get_att_live_stats", views.get_attendance_live_stats, name="mgr_get_attendance_live_stats"),
        path("force_logout_attendance", views.force_logout_attendance, name="force_logout_attendance"),
        path("toggle_break", views.toggle_break),
        path("break_status", views.break_status),
        path("get_all_team_break", views.GetAllTeamBreak.as_view(), name="get_all_team_break"),
        path("get_all_consolidated_team_break", views.GetConsolidatedAllTeamBreak.as_view(),
             name="get_all_consolidated_team_break"),
        path("direct_attendance_marking_by_cc", views.direct_attendance_marking_by_cc,
             name="direct_attendance_marking_by_ccteam_only"),
        path("direct_attendance_marking", views.direct_attendance_marking,
             name="direct_attendance_marking"),
        path("create_schedule_manually", views.create_schedule_manually, name="create_schedule_manually"),
        path('get_checkin_report', views.get_checkin_report, name="get_checkin_report"),
        path('suspicious_activity_report', views.suspicious_activity_report,
             name="suspicious_activity_report_ccteam_only"),
        path("get_leave_balance_history_report", views.get_leave_balance_history_report,
             name="get_leave_balance_history_report"),
        path("add_holiday", views.add_holiday, name="add_holiday"),
        path("export-turnstile-report", views.exportTurnstileReport, name='export_attendance_csv'),
        path("get_all_biometric_log",views.GetAllBiometricLog.as_view(),name="get_all_biometric_log"),

        path('attendance/update/', BulkAttendanceRangeUpdateView.as_view(), name='attendance-update'),
        path('update_mcl/<str:emp_id>', views.update_mcl, name="update_mcl"),
        path("download_leave_report", views.download_leave_report, name="download_leave_report"),

    ]
