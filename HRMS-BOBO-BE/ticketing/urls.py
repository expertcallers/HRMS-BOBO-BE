from django.urls import path
from . import views

urlpatterns = [
    path('create_ticket', views.create_ticket),
    path("get_all_tickets", views.GetAllTickets.as_view(), name="get_all_tickets"),
    path("get_dept_all_tickets", views.GetDeptAllTickets.as_view(), name="get_dept_all_tickets"),
    path("get_dept_spam_tickets", views.GetDeptSpamTickets.as_view()),
    path("get_my_tickets", views.GetMyTickets.as_view()),
    path("assign_ticket/<str:ticket_id>", views.assign_ticket),
    path("get_ticket_history/<int:ticket_id>", views.GetTicketHistory.as_view()),
    path("create_ticket_message/<int:ticket_id>", views.create_ticket_message),
    path("create_ticket_msg_reply/<int:tkt_msg_id>", views.create_ticket_msg_reply),
    path('get_ticket_messages/<int:ticket_id>', views.GetTicketMessage.as_view()),
    path('get_no_of_open_tickets', views.get_no_of_open_tickets, name="get_no_of_open_tickets"),
    path('get_ticket_sub_category/<int:dept_id>', views.get_ticket_sub_category),
    path('resolve_ticket/<int:ticket_id>', views.resolve_ticket),
    path('change_ticket_status/<int:ticket_id>', views.change_ticket_status),
    path('close_ticket/<int:ticket_id>', views.close_ticket),
    path('get_ticket_info/<int:ticket_id>', views.get_ticket_info),
    path('document/<str:doc_id>', views.get_document),
]
