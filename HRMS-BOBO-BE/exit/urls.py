from django.urls import path
from exit import views

urlpatterns = [
    path('apply_resignation', views.apply_resignation),
    path('get_resignation_status', views.get_resignation_status),
    path('get_my_team_applied_resignation', views.GetmyTeamAppliedResignation.as_view(),
         name="get_my_team_applied_resignation"),
    path('approve_applied_resignation', views.GetAllApproveAppliedResignation.as_view(),
         name="approve_applied_resignation"),
    path('get_all_applied_resignation', views.GetAllAppliedResignation.as_view(), name="get_all_applied_resignation"),
    path('approve_resignation/<int:resign_id>', views.approve_resignation, name="approve_resignation"),
    path('get_resignation_history', views.get_resignation_history),
    path('update_notice_period/<int:resign_id>', views.update_notice_period, name="update_notice_period"),
    path('withdraw_resignation', views.withdraw_resignation),
    path('submit_exit_feedback', views.submit_exit_feedback),
    path('view_team_exit_feedback/<int:resign_id>', views.view_team_exit_feedback, name="view_team_exit_feedback"),
    path('get_exit_checklist/<int:resign_id>', views.get_exit_checklist, name="view_team_exit_feedback"),
    path('final_approval/<int:resign_id>', views.final_exit_approval, name='final_approval'),
    path('view_final_approval/<int:resign_id>', views.view_final_exit_approval, name='view_final_approval'),
    path('terminate/<str:emp_id>', views.terminate, name='terminate'),

]
