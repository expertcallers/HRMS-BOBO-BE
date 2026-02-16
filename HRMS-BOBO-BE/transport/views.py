import logging
import traceback

from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from mapping.views import HasUrlPermission
from transport.models import CabDetail
from transport.serializers import CabAddressDetailSerializer, CabAddressDetailUpdateSerializer
from utils.sort_and_filter_by_cols import get_sort_and_filter_by_cols
from utils.utils import return_error_response, get_cab_address_obj_by_cab_address_id

logger = logging.getLogger(__name__)


# Create your views here.
class CabAddressDetail(ListModelMixin, GenericAPIView):
    serializer_class = CabAddressDetailSerializer

    def get_permissions(self):
        if self.request.method in ['PATCH']:
            return [IsAuthenticated(), HasUrlPermission()]  # Permission for GET requests
        else:
            return [AllowAny()]  # No authentication required for POST requests

    def get(self, request, *args, **kwargs):
        try:
            map_columns = {"emp_id": "employee__emp_id"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=map_columns)
            cab_address_id = kwargs.get("cab_address_id")
            if cab_address_id:
                cab_address = get_cab_address_obj_by_cab_address_id(cab_address_id)
                return Response({"cab_address": self.serializer_class(cab_address).data})
            self.queryset = CabDetail.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info("exception at CabAddressDetail.GET {0}".format(traceback.format_exc()))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        try:
            cab_address_id = kwargs.get("cab_address_id")
            cab_address = CabDetail.objects.filter(id=cab_address_id).first()
            if cab_address is None:
                raise ValueError("The requested cab-address does not exist")
            if cab_address.candidate is None:
                raise ValueError(f"There is no candidate linked to this cab-address")
            if cab_address.candidate.transport_approval_status == "Rejected":
                raise ValueError(
                    f"This cab details is already rejected by {cab_address.candidate.transport_admin_app_rej_by.full_name}")
            serializer = CabAddressDetailUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return_error_response(serializer, raise_exception=True)
            serializer.validated_data["updated_by"] = request.user
            serializer.update(cab_address, serializer.validated_data)
            return Response({"message": "Cab address updated successfully"})
        except Exception as e:
            logger.info("exception at CabAddressDetail.GET {0}".format(traceback.format_exc()))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
