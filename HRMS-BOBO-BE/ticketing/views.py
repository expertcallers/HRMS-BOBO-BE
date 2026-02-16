import logging
import traceback
from datetime import datetime
from django.http import HttpResponse
import json
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from mapping.models import Profile
from mapping.views import HasUrlPermission
from ticketing.models import Ticket, TicketHistory, Document, TicketMessage, SubCategory
from ticketing.serializers import CreateTicketSerializer, GetAllTicketsSerializer, UpdateTicketStatusSerializer, \
    GetTicketHistorySerializer, CreateTicketMessageSerializer, CreateTicketReplySerializer, \
    GetAllTicketMessageSerializer, SubCategorySerializer, ResolveTicketSerializer, CloseTicketSerializer
from utils.util_classes import CustomTokenAuthentication
from utils.utils import get_formatted_name, return_error_response, get_sort_and_filter_by_cols, update_request, \
    document_response

logger = logging.getLogger(__name__)


def create_file(field, file, user=None):
    emp_id = user.emp_id if user else None
    name = get_formatted_name(user) if user else None
    document = Document(field=field, file=file, uploaded_by_emp_id=emp_id, uploaded_by_name=name, file_name=file.name)
    return document


def get_ticket_by_id(ticket_id):
    ticket = Ticket.objects.filter(id=ticket_id).last()
    if ticket is None:
        raise ValueError("Invalid Ticket ID")
    return ticket


def create_ticket_history(ticket, transaction, created_by):
    TicketHistory.objects.create(ticket=ticket, created_by=created_by, transaction=transaction)
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def get_document(request, doc_id):
    return document_response(Document, doc_id)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_ticket(request):
    tkt_files = []
    try:
        usr = request.user
        created_for_emp_id = request.data.get("created_for")
        if created_for_emp_id:
            created_for = Profile.objects.filter(emp_id=created_for_emp_id)
            if not created_for:
                raise ValueError("User with {0} emp_id doesn't exist".format(created_for_emp_id))
            data = update_request(request.data, created_by=usr.id, created_for=created_for.last().id)
        else:
            data = update_request(request.data, created_by=usr.id, created_for=usr.id)
        serializer = CreateTicketSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        files = request.FILES.getlist('ticketing_docs')
        if files and type(files) == list:
            for i in files:
                document = create_file('tkt_attachments', i, user=usr)
                if document:
                    tkt_files.append(document)

        ticket = serializer.create(serializer.validated_data)
        create_ticket_history(ticket=ticket,
                              transaction="New ticket has been raised; ID:{0}, by {1}({2})".format(ticket.id,
                                                                                                   get_formatted_name(
                                                                                                       usr),
                                                                                                   usr.emp_id),
                              created_by=usr)

        if len(tkt_files) > 0:
            for doc in tkt_files:
                doc.ticket_id = ticket.id
                doc.save()
                ticket.tkt_attachments.add(doc)

        return HttpResponse(json.dumps({"message": "Ticket created successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllTickets(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllTicketsSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user
        fields_look_up = {"assigned_to_emp_id": "assigned_to__emp_id", "assigned_to_name": "assigned_to__full_name",
                          "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                          "created_for_emp_id": "created_for__emp_id", "created_for_name": "created_for__full_name",
                          "to_dept": "to_dept__name", "from_dept": "created_by__department__name",
                          'priority': "sub_category__priority", 'sub_category': "sub_category__sub_category",
                          'tat_days': "sub_category__tat_days"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Ticket.objects.filter(search_query).filter(**filter_by).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


class GetDeptAllTickets(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllTicketsSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user
        fields_look_up = {"assigned_to_emp_id": "assigned_to__emp_id", "assigned_to_name": "assigned_to__full_name",
                          "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                          "created_for_emp_id": "created_for__emp_id", "created_for_name": "created_for__full_name",
                          "to_dept": "to_dept__name", "from_dept": "created_by__department__name",
                          'priority': "sub_category__priority", 'sub_category': "sub_category__sub_category",
                          'tat_days': "sub_category__tat_days"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Ticket.objects.filter(to_dept=usr.designation.department).exclude(status="Spam").filter(
            search_query).filter(**filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetDeptSpamTickets(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllTicketsSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user
        fields_look_up = {"assigned_to_emp_id": "assigned_to__emp_id", "assigned_to_name": "assigned_to__full_name",
                          "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                          "created_for_emp_id": "created_for__emp_id", "created_for_name": "created_for__full_name",
                          "to_dept": "to_dept__name", "from_dept": "created_by__department__name",
                          'priority': "sub_category__priority", 'sub_category': "sub_category__sub_category",
                          'tat_days': "sub_category__tat_days"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Ticket.objects.filter(to_dept=usr.designation.department, status="Spam").filter(
            search_query).filter(
            **filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetMyTickets(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllTicketsSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user
        fields_look_up = {"assigned_to_emp_id": "assigned_to__emp_id", "assigned_to_name": "assigned_to__full_name",
                          "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                          "created_for_emp_id": "created_for__emp_id", "created_for_name": "created_for__full_name",
                          "to_dept": "to_dept__name", "from_dept": "created_by__department__name",
                          'priority': "sub_category__priority", 'sub_category': "sub_category__sub_category",
                          'tat_days': "sub_category__tat_days"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Ticket.objects.filter(created_by=usr).filter(search_query).filter(**filter_by).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def assign_ticket(request, ticket_id):
    try:
        usr = request.user
        ticket = get_ticket_by_id(ticket_id)
        create_ticket_history(ticket=ticket,
                              transaction="Ticket assigned to {0} at {1}".format(get_formatted_name(usr),
                                                                                 datetime.now()), created_by=usr)
        ticket.assigned_to = usr
        ticket.save()
        return HttpResponse(json.dumps({"message": "Ticket assigned successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetTicketHistory(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetTicketHistorySerializer
    model = serializer_class.Meta.model

    def get(self, request, ticket_id, *args, **kwargs):
        map_columns = {"created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = TicketHistory.objects.filter(ticket_id=ticket_id).filter(search_query).filter(
            **filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_ticket_message(request, ticket_id):
    try:
        usr = request.user
        ticket = get_ticket_by_id(ticket_id)
        serializer = CreateTicketMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["ticket"] = ticket
        serializer.validated_data["created_by"] = usr

        files = request.FILES.getlist('message_docs')
        msg_docs_list = []
        if files and type(files) == list:
            for i in files:
                document = create_file('msg_attachments', i, user=usr)
                if document:
                    msg_docs_list.append(document)
        serializer.msg_attachments = []
        tkt_message = serializer.create(serializer.validated_data)
        if len(msg_docs_list) > 0:
            for doc in msg_docs_list:
                doc.ticket_id = ticket.id
                doc.save()
                tkt_message.msg_attachments.add(doc)
        return HttpResponse(json.dumps({"message": "ticket created successfully"}))
    except Exception as e:
        logger.info("exception at create_ticket_message {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_ticket_msg_by_id(tkt_msg_id):
    tkt_message = TicketMessage.objects.filter(id=tkt_msg_id).last()
    if tkt_message is None:
        raise ValueError("Invalid ticket message id")
    return tkt_message


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_ticket_msg_reply(request, tkt_msg_id):
    try:
        usr = request.user
        tkt_message = get_ticket_msg_by_id(tkt_msg_id)
        serializer = CreateTicketReplySerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["created_by"] = usr
        tkt_reply = serializer.create(serializer.validated_data)
        tkt_message.replies.add(tkt_reply)
        files = request.FILES.getlist('message_docs')
        reply_docs_list = []
        if files and type(files) == list:
            for i in files:
                document = create_file('reply_attachments', i, user=usr)
                if document:
                    reply_docs_list.append(document)
        serializer.msg_attachments = []
        if len(reply_docs_list) > 0:
            for doc in reply_docs_list:
                doc.ticket_id = tkt_message.ticket.id
                doc.save()
                tkt_reply.reply_attachments.add(doc)
        return HttpResponse(json.dumps({"message": "ticket reply created successfully"}))
    except Exception as e:
        logger.info("exception at create_ticket_msg_reply {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetTicketMessage(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllTicketMessageSerializer
    model = serializer_class.Meta.model

    def get(self, request, ticket_id, *args, **kwargs):
        map_columns = {"created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)

        self.queryset = TicketMessage.objects.filter(ticket_id=ticket_id).filter(search_query).filter(
            **filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_no_of_open_tickets(request):
    try:
        usr = request.user
        open_tickets = Ticket.objects.filter(status="Open", to_dept=usr.designation.department).count()
        return HttpResponse(json.dumps({"count": open_tickets}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": e}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_ticket_sub_category(request, dept_id):
    try:
        sub_category = SubCategory.objects.filter(dept=dept_id)
        sub_category = SubCategorySerializer(sub_category, many=True).data
        return HttpResponse(json.dumps({"sub_category": sub_category}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": e}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def resolve_ticket(request, ticket_id):
    tkt_files = []
    try:
        data = request.data
        usr = request.user
        if not data.get("resolve_comment"):
            raise ValueError("Comment is required.")
        logger.info("data attachment{0}".format(data))
        serializer = ResolveTicketSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        files = request.FILES.getlist('closing_attachments')
        logger.info("closing attachment{0}".format(files))
        if files and type(files) == list:
            for i in files:
                document = create_file('tkt_attachments', i, user=usr)
                if document:
                    tkt_files.append(document)

        ticket = get_ticket_by_id(ticket_id)
        if not ticket.to_dept == usr.designation.department:
            raise ValueError("Action not allowed.")
        ticket.resolved_by = usr
        ticket.status = "Resolved"
        ticket.resolve_comment = serializer.validated_data["resolve_comment"]
        ticket.save()
        create_ticket_history(ticket=ticket, created_by=usr,
                              transaction="Ticket has been resolved by {0} at {1}".format(get_formatted_name(usr),
                                                                                          datetime.now()))
        if len(tkt_files) > 0:
            for doc in tkt_files:
                doc.ticket_id = ticket.id
                doc.save()
                ticket.closing_attachments.add(doc)
        return HttpResponse(json.dumps({"message": "Ticket resolved successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def change_ticket_status(request, ticket_id):
    try:
        usr = request.user
        serializer = UpdateTicketStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        ticket = get_ticket_by_id(ticket_id)
        old_status = ticket.status
        if old_status == "Resolved" or old_status == "Closed":
            raise ValueError("Ticket Status has already been set to {0}".format(old_status))
        if not ticket.to_dept == usr.designation.department:
            raise ValueError("Action not allowed.")
        tkt_status = serializer.validated_data["status"]
        ticket.status = tkt_status
        ticket.save()
        create_ticket_history(ticket=ticket, created_by=usr,
                              transaction="Ticket Status changed from {0} to {1} by {2} at {3}".format(old_status,
                                                                                                       tkt_status,
                                                                                                       get_formatted_name(
                                                                                                           usr),
                                                                                                       datetime.now()))
        return HttpResponse(json.dumps({"message": "Ticket Status changed Successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def close_ticket(request, ticket_id):
    try:
        data = request.data
        usr = request.user
        if not data.get("closed_comment") and data.get("user_rating"):
            raise ValueError("Comment & Rating is required.")
        ticket = get_ticket_by_id(ticket_id)
        if not usr == ticket.created_by:
            raise ValueError("This ticket wasn't raised by you. You aren't allowed to close the Ticket.")
        if not ticket.status == "Resolved":
            raise ValueError("Ticket Status set to {0}. Action not allowed.".format(ticket.status))
        serializer = CloseTicketSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        ticket.status = "Closed"
        ticket.user_rating = serializer.validated_data["user_rating"]
        ticket.closed_comment = serializer.validated_data["closed_comment"]
        ticket.closed_at = datetime.now()
        ticket.save()
        create_ticket_history(ticket=ticket, created_by=usr,
                              transaction="Ticket has been Closed at {0} with {1} Rating".format(datetime.now(),
                                                                                                 ticket.user_rating))
        return HttpResponse(json.dumps({"message": "Ticket Closed successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_ticket_info(request, ticket_id):
    try:
        ticket = get_ticket_by_id(ticket_id)
        serializer = GetAllTicketsSerializer(ticket).data
        return HttpResponse(json.dumps({"ticket": serializer}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
