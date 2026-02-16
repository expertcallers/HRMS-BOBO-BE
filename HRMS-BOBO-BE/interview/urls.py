from django.core.management.commands.runserver import naiveip_re
from django.urls import path

from hrms import settings
from interview import views

# TODO Add reject candidate with comment
urlpatterns = [
    path('register_otp', views.create_candidate_otp),
    path('send_email_otp', views.send_email_otp),
    path('verify_email_otp', views.verify_candidate_email_otp),
    path("create_application_otp/<str:cd_id>", views.create_application_otp),
    path('update_candidate_otp/<str:cd_id>', views.update_candidate_otp),
    path('status_otp', views.get_candidate_status),
    path("position", views.get_positions, name="intern_positions"),
    path('question/<str:position_id>', views.get_questions, name="intern_questions"),
    path("intern_application", views.submit_intern_application, name="intern submit"),
    path("export_intern_applications", views.export_intern_applications, name="export_intern_ccteam_only")
]
if not settings.IS_PUBLIC_SERVER:
    urlpatterns += [
        path('get_pending_interviews', views.get_pending_interviews),
        path('feedback/<str:cd_id>', views.get_feedback),
        path('feedback_history/<str:cd_id>', views.GetAllFeedbackHistory.as_view()),
        path('get_interview_round/<str:cd_id>', views.get_interview_round),
        path('candidate/<str:id>', views.get_candidate, name='get_candidate_by_id'),
        path('create_interview_feedback/<str:cd_id>', views.candidate_interview_feedback,
             name='create_interview_feedback'),
        path('candidate', views.GetAllCandidateInfo.as_view(), name="get_all_candidate"),
        path('candidate_list_for_transport_approval', views.GetAllTransportApprovalCandidateInfo.as_view(),
             name="candidate_list_for_transport_approval"),
        path('update_candidate/<str:cd_id>', views.update_candidate),
        path('document/<str:doc_id>', views.get_document),
        path("update_candidate_erf/<str:cnd_id>", views.update_candidate_erf),
        path('get_count_by_waiting_duration', views.get_count_by_waiting_duration,
             name="get_count_by_waiting_duration"),
        path("update_fields_of_exp", views.update_fields_of_exp),
        path("add_interview_doc/<str:feedback_id>", views.add_interview_doc),
        path("get_interview_docs/<str:feedback_id>", views.get_interview_docs),
        path("edit_next_interviewer/<str:feedback_id>", views.edit_next_interviewer, name="edit_next_interviewer"),
        path("edit_candidate/<str:cd_id>", views.edit_candidate, name="edit_ta_hr_candidate"),
        path("edit_job_application/<str:cd_id>", views.edit_job_application, name="edit_ta_hr_job_application"),
        path("send_back_candidate_to_applied_status/<str:cd_id>", views.send_back_candidate_to_applied_status,
             name="send_back_candidate_to_applied_status"),
        path("save_file_from_public_server", views.save_file_from_public_server),
        path("transport_approval/<str:cd_id>", views.transport_approval, name="transport_approval")

    ]
