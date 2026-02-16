from django.urls import path
from it import views

urlpatterns = [
    path("create_change_mgmt", views.create_change_mgmt, name="create_change_mgmt"),
    path("approve_change_mgmt/<str:cm_id>", views.approve_change_mgmt, name="approve_change_mgmt"),
    path("review_change_mgmt/<str:cm_id>", views.review_change_mgmt, name="review_change_mgmt"),
    path("edit_change_mgmt/<str:cm_id>", views.edit_change_mgmt, name="edit_change_mgmt"),
    path("get_my_change_mgmt", views.GetMyChangeMgmt.as_view(), name="get_my_change_mgmt"),
    path("get_all_change_mgmt", views.GetAllChangeMgmt.as_view(), name="get_all_change_mgmt"),
    path("get_all_approvals_change_mgmt", views.GetAllApprovalsChangeMgmt.as_view(),
         name="get_all_approvals_change_mgmt"),
    path("get_all_approvals_change_mgmt", views.GetAllApprovalsChangeMgmt.as_view(),
         name="get_all_approvals_change_mgmt"),

    path("get_all_reviews_change_mgmt", views.GetAllReviewsChangeMgmt.as_view(),
         name="get_all_reviews_change_mgmt"),
    path("get_next_document_reference_number",views.get_next_document_reference_number)
]
