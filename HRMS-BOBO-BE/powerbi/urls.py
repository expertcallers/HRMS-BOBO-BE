from django.urls import path

from powerbi import views

urlpatterns = [
    path("create_sop", views.create_sop, name="create_sop"),
    path("get_all_sop", views.GetAllSOP.as_view(), name="get_all_sop"),
    path("get_sop/<str:sop_id>", views.get_sop, name="get_sop"),
    path("update_sop_status/<str:sop_id>", views.update_sop_status, name="update_sop_status")
]
