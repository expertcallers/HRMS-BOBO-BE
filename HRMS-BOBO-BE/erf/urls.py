from django.urls import path

from erf import views

urlpatterns = [
    path('create_erf', views.create_erf, name="create_erf"),
    path('update_erf_approval_status', views.update_erf_approval_status, name="update_erf_approval_status"),
    path('get_all_erf', views.GetAllErf.as_view(), name="get_all_erf"),
    path('get_erf/<str:erf_id>', views.get_erf, name="get_erf_by_id"),
    path('get_erf_candidates/<str:erf_id>', views.GetErfProfiles.as_view(), name="get_erf_candidates_list_by_erf_id"),
    path('get_my_erf', views.GetMyErf.as_view(), name="get_my_erf"),
    path('get_my_erf_stats', views.get_my_erf_stats, name="get_my_erf_stats"),
    path('get_all_erf_stats', views.get_all_erf_stats, name="get_all_erf_stats"),
    path('get_all_open_erf', views.get_all_open_erf),
    path('unlink_erf/<str:erf_id>/<str:emp_id>', views.unlink_erf, name="unlink_erf"),
    path("get_erf_history/<int:erf_id>", views.GetErfHistory.as_view()),
    path("close_erf_by_mgr/<int:erf_id>", views.close_erf_by_mgr, name="close_erf_by_mgr")
]
