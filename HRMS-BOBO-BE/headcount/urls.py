from django.urls import path
from headcount import views

urlpatterns = [
    path("create_process", views.create_process, name="create_hc_process"),
    path("get_all_process", views.GetAllProcess.as_view(), name="get_all_process"),
    path("request_for_update_process/<int:proc_id>", views.request_for_update_process,
         name="request_for_update_process"),
    path("get_all_process_request", views.GetAllProcessRequest.as_view(), name="get_all_process_request"),
    path("approve_process/<int:req_id>", views.approve_process, name="approve_process"),
    path("get_all_hc_process", views.get_all_hc_process),
    path("get_subcampaign_by_process/<int:proc_id>", views.get_subcampaign_by_process),
    path("update_today_hc", views.update_today_hc, name="update_today_hc"),
    path("get_all_hc_by_process", views.GetHeadcountByProcess.as_view(), name="get_all_hc_by_process"),
    path("get_headcount_info_for_update/<int:ref_id>", views.get_headcount_info_for_update,
         name="get_headcount_info_for_update"),
    path("update_headcount/<int:hc_id>", views.update_headcount, name="update_headcount"),
    path("get_all_hc_request", views.GetAllHeadcountRequest.as_view(), name="get_all_hc_request"),
    path("approve_update_headcount/<int:req_id>", views.approve_update_headcount, name="approve_update_headcount"),
    path("export_headcount", views.export_headcount, name="export_headcount")
]
