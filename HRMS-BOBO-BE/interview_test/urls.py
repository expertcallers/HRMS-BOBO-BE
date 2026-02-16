from django.urls import path

from hrms import settings
from interview_test import views

urlpatterns = [
    path("get_questions_by_test/<str:cd_id>", views.get_test_questions_by_test_name),
    path("start_end_status_test/<str:cd_id>", views.start_end_status_test),
    path("submit_test_answer", views.submit_test_answer),
    path("test_info/<int:test_id>", views.get_test_info),
]
if not settings.IS_PUBLIC_SERVER:
    urlpatterns += [
        path("create_test", views.create_test),
        path("get_all_tests_list", views.get_all_tests_list),
        path("upload_test_questions", views.upload_test_questions, name="upload_test_questions"),
        # path("get_questions_by_test_section/<int:ts_id>", views.GetTestQuestionsByTestSection.as_view()),
        path("get_all_interview_test_timing", views.GetAllInterviewTestTiming.as_view(),
             name="get_all_interview_test_timing"),
        path("get_candidate_interview_test_timing_history/<str:candidate_id>",
             views.GetCandidateInterviewTestTiming.as_view()),
        path("get_all_test_qa", views.GetAllTestQA.as_view(), name="get_all_interview_questions_answers"),
        path("get_all_test", views.GetAllTest.as_view(), name="get_all_test"),
        path("update_qa/<str:qa_id>", views.update_qa, name="update_qa"),
        path("update_test/<str:test_id>", views.update_test, name="update_test"),
        path("update_test_section/<str:test_section_id>", views.update_test_section, name="update_test_section"),
        path("update_pre_data/<str:pre_data_id>", views.update_pre_data, name="update_pre_data"),
        path("get_all_answered_qns_ans", views.GetAllCandidateInterviewTest.as_view(), name="get_all_answered_qns_ans"),
        #    path("cand_test_timing",views.get_candidate_test_timing),
    ]
# TODO handle leave balance at the end of january
# {"type": "mcq",
#  "test_name": "",
#  "test_section": "",
#  "pre_data_title": "",
#  "pre_data_content": "",
#  "questions": [
#      {"id": '', "option_1": "", "option_2": "", "option_3": "", "option_4": "", "option_5": "","type":[]
#       "question": ""}]}
#
# {"type": "text_qa",
#  "test_name": "",
#  "test_section": "",
#  "pre_data_title": "",
#  "pre_data_content": "",
#  "questions": [
#      {"id": '', "question_1": "", "question_2": "", "question_3": "", }]}
