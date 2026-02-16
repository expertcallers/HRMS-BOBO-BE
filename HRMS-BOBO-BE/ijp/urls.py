from django.urls import path
from .views import *

urlpatterns = [
    path('create_new_ijp', create_new_ijp, name="create_new_ijp"),
    path('get_all_ijp', GetAllIJP.as_view(), name="get_all_ijp"),
    path('close_ijp/<int:ijp_id>', close_ijp, name="close_ijp"),
    path('get_ijp_info/<int:id>', get_ijp_info),
    path('get_all_ijp_applications/<int:ijp_id>', GetIJPApplications.as_view()),
    # path('update_ijp_approval_status', update_ijp_approval_status),
    path('apply_to_ijp/<int:ijp_id>', apply_to_ijp),
    path('get_no_of_open_ijp', get_no_of_open_ijp),
    path('get_all_unapplied_ijp', GetAllUnappliedIJP.as_view()),
    path("get_open_ijp_list", GetOpenIJP.as_view()),
    path('change_ijp_candidate_status/<str:cand_id>', change_ijp_candidate_status),
]
