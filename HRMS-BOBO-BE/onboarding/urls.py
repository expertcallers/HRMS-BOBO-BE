from django.urls import path

from hrms import settings
from onboarding import views

urlpatterns = [
    path('public_delete/doc/<str:doc_id>', views.public_delete_document),
    path('public_create/<str:cd_id>', views.public_create_onboard),
]
if not settings.IS_PUBLIC_SERVER:
    urlpatterns += [
        path('create/<str:cd_id>', views.create_onboard, name='create_onboard_by_cd_id'),
        path('update/<str:ob_id>', views.update_onboard_employee, name='update_onboard_by_ob_id'),
        path('delete/doc/<str:doc_id>', views.delete_document, name='delete_document_by_doc_id'),
        path('get/<str:ob_id>', views.get_onboard, name="get_onboard_by_ob_id"),
        path('get_so', views.GetAllSelectedForOnboardInfo.as_view(), name="get_all_selected_for_onboard"),
        path('get', views.GetAllOnboardInfo.as_view(), name="get_all_onboard"),
        path('document/<str:doc_id>', views.get_document),
        path('send_appointment_letter/<str:cd_id>', views.send_appointment_letter,
             name='send_appointment_letter_by_cd_id'),
        path('send_offer_letter/<str:cd_id>', views.send_offer_letter, name='send_offer_letter_by_cd_id'),
        path('update_offer_response/<str:cd_id>', views.update_offer_response, name='update_offer_response_by_cd_id'),
        # path("get_appointment_letter_content", views.get_appointment_letter_content, name='get_appointment_letter_content'),
        path("upload_health_card", views.upload_health_card, name="upload_health_card"),
        path("upload_onboard_details", views.upload_onboard_details, name="upload_onboard_details"),
        path("update_candidate_onboard_details", views.update_candidate_onboard_details),
        path("archive_candidate/<cd_id>", views.archive_candidate),
        path("update_already_onboarded_candidate_status/<str:op_id>", views.update_already_onboarded_candidate_status)
    ]
