import logging
import traceback

from django.core.validators import validate_email
from django.shortcuts import render
from django.http import HttpResponse
import json
from num2words import num2words
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin

from po.serializers import SupplierSerializer, BillSerializer, ItemDescriptionSerializer, SupplierInfoSerializer, \
    BillInfoSerializer, UpdateSupplierSerializer
from po.models import BillAdministration, SupplierAdministration, BillItemDescription
from utils.util_classes import CustomTokenAuthentication
from utils.utils import update_request, return_error_response, get_sort_and_filter_by_cols, \
    check_for_integrity_error, validate_model_field, validate_bnk_account_no
from mapping.views import HasUrlPermission
from mapping.models import MiscellaneousMiniFields
from hrms import settings

logger = logging.getLogger(__name__)


def get_all_item_by_po_id(po_id):
    try:
        if not po_id:
            raise ValueError("Please provide valid PO ID")
        po = BillItemDescription.objects.filter(bill=po_id)
        return po
    except Exception as e:
        raise None


def get_po_by_po_id(po_id):
    try:
        if not po_id:
            raise ValueError("Please provide valid PO ID")
        po = BillAdministration.objects.filter(id=po_id).last()
        return po
    except Exception as e:
        raise ValueError("PO with this ID not found")


def get_item_by_id(item_id, po_id):
    if not item_id:
        raise ValueError("Please provide valid Item ID")
    item = BillItemDescription.objects.filter(id=item_id).last()
    if item is None:
        raise ValueError("Item with this ID not found")
    if item.bill.id != po_id:
        raise ValueError("Item Description is provided for this po")
    return item


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_po(request):
    try:
        data = request.data
        billing_office = data.get("billing_office")
        delivery_office = data.get("delivery_office")
        po_number = MiscellaneousMiniFields.objects.filter(field="po_number").last()
        if po_number is None:
            raise ValueError("contact-admin, add misc-mini default value for po-number")
        if delivery_office == "Kothanur Office":
            po_no = "E2" + str(po_number.content)
        else:
            po_no = "E1" + str(po_number.content)
        po_number.content = int(po_number.content) + 1
        billing_office = settings.PO_OFFICE_ADDRESS[billing_office]
        delivery_address = settings.PO_OFFICE_ADDRESS[delivery_office]
        supplier = data.get("supplier")
        data = update_request(request.data, created_by=request.user.id, billing_office=billing_office,
                              delivery_address=delivery_address, delivery_office=settings.DELIVERY_OFFICE,
                              supplier=int(supplier), po_no=po_no)
        serializer = BillSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        po = serializer.create(serializer.validated_data)
        description = data.get("description_items")
        item_desc_list = []
        for desc in description:
            desc = update_request(desc, created_by=request.user.id, bill=po.id)
            serializer = ItemDescriptionSerializer(data=desc)
            if not serializer.is_valid():
                po.delete()
                return return_error_response(serializer)
            serializer.validated_data["amount"] = serializer.validated_data["quantity"] * serializer.validated_data[
                "price"]
            serializer.validated_data["gst_amount"] = serializer.validated_data["amount"] * serializer.validated_data[
                "gst_percent"] / 100
            item_desc_list.append(BillItemDescription(**serializer.validated_data))
        if len(item_desc_list) > 0:
            BillItemDescription.objects.bulk_create(item_desc_list)
        all_item = get_all_item_by_po_id(po.id)
        if not all_item:
            raise ValueError("No Item Description created for this PO.")
        total_amount = 0
        gst_amount = 0
        for item in all_item:
            total_amount += item.amount
            gst_amount += item.gst_amount
        grand_total = round(total_amount + gst_amount, 2)
        amount_words = num2words(grand_total, lang='en_IN')
        amount_words = amount_words.replace(',', '')
        po.total_amount = round(total_amount, 2)
        po.gst_amount = round(gst_amount, 2)
        po.grand_total = grand_total
        po.amount_in_words = amount_words
        po.save()
        po_number.save()
        return HttpResponse(json.dumps({"message": "PO created successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_supplier(request):
    try:
        usr = request.user
        data = update_request(request.data, created_by=usr.id)
        serializer = SupplierSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        supplier = serializer.create(serializer.validated_data)
        return HttpResponse(json.dumps({"message": "Supplier created successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_supplier(request):
    try:
        supplier = list(SupplierAdministration.objects.values_list("id", "name", named=True))
        return HttpResponse(json.dumps({"results": supplier}))
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllSupplierInfo(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = SupplierInfoSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"created_by_name": "created_by__full_name", "created_by_emp_id": "created_by__emp_id"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = SupplierAdministration.objects.all().filter(**filter_by).filter(search_query).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


class GetAllPOInfo(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = BillInfoSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"created_by_name": "created_by__full_name", "created_by_emp_id": "created_by__emp_id",
                       "supplier_name": "supplier__name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = BillAdministration.objects.all().filter(**filter_by).filter(search_query).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_po(request, po_id):
    try:
        data = request.data
        billing_office = data.get("billing_office")
        delivery_office = data.get("delivery_office")
        billing_office = settings.PO_OFFICE_ADDRESS[billing_office]
        delivery_address = settings.PO_OFFICE_ADDRESS[delivery_office]
        supplier = data.get("supplier")
        po = get_po_by_po_id(po_id)
        data = update_request(request.data, created_by=request.user.id, billing_office=billing_office,
                              delivery_address=delivery_address, delivery_office=settings.DELIVERY_OFFICE,
                              supplier=int(supplier), po_no=po.po_no)
        serializer = BillSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer, raise_exception=True)
        po = serializer.update(po, serializer.validated_data)
        description = data.get("description_items")
        existing_desc = BillItemDescription.objects.filter(bill__id=po.id)
        updated_desc_ids = {}
        new_desc = []
        for desc in description:
            desc = update_request(desc, created_by=request.user.id, bill=po.id)
            serializer = ItemDescriptionSerializer(data=desc)
            if not serializer.is_valid():
                return return_error_response(serializer, raise_exception=True)
            serializer.validated_data["amount"] = serializer.validated_data["quantity"] * serializer.validated_data[
                "price"]
            serializer.validated_data["gst_amount"] = serializer.validated_data["amount"] * serializer.validated_data[
                "gst_percent"] / 100
            if desc.get("id") is None:
                serializer.validated_data['bill'] = po
                new_desc.append(serializer.validated_data)
            else:
                updated_desc_ids[desc.get("id")] = serializer.validated_data
        update_obj_list = []
        for key, value in updated_desc_ids.items():
            item = get_item_by_id(key, po.id)
            for ikey, ival in value.items():
                setattr(item, ikey, ival)
            update_obj_list.append(item)

        removed_desc = []
        for edesc in existing_desc:
            if edesc.id not in updated_desc_ids.keys():
                removed_desc.append(edesc)
        for rem_desc in removed_desc:
            rem_desc.delete()
        for ndesc in new_desc:
            BillItemDescription.objects.create(**ndesc)
        BillItemDescription.objects.bulk_update(update_obj_list,
                                                ["description", "quantity", "gst_percent", "gst_amount", "price",
                                                 "amount"])
        all_item = get_all_item_by_po_id(po.id)
        if not all_item:
            raise ValueError("No Item Description created for this PO.")
        total_amount = 0
        gst_amount = 0
        for item in all_item:
            total_amount += item.amount
            gst_amount += item.gst_amount
        grand_total = round(total_amount + gst_amount, 2)
        amount_words = num2words(grand_total, lang='en_IN')
        amount_words = amount_words.replace(',', '')
        po.total_amount = total_amount
        po.gst_amount = gst_amount
        po.grand_total = grand_total
        po.amount_in_words = amount_words
        po.save()
        return HttpResponse(json.dumps({"message": "PO updated successfully."}))
    except Exception as e:
        logger.info("exception at update_po {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_supplier(request, supplier_id):
    try:
        data = request.data
        if not supplier_id:
            raise ValueError("Please provide valid Supplier ID")
        supplier = SupplierAdministration.objects.filter(id=supplier_id).last()
        if not supplier:
            raise ValueError("Supplier with this ID not found.")
        contact_email = data.get("contact_email")
        validate_model_field(contact_email, validate_email)
        account_number = data.get("account_number")
        validate_model_field(account_number, validate_bnk_account_no)
        serializer = UpdateSupplierSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        supplier = check_for_integrity_error("contact_email", contact_email, supplier)
        supplier = check_for_integrity_error("name", data.get("name"), supplier)
        supplier = check_for_integrity_error("account_number", account_number, supplier)
        supplier = check_for_integrity_error("pan_no", data.get("pan_no"), supplier)
        supplier = check_for_integrity_error("gst", data.get("gst"), supplier)
        serializer.update(supplier, serializer.validated_data)
        supplier.save()
        return HttpResponse(json.dumps({"message": "Supplier updated successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_supplier_info(request, supplier_id):
    try:
        if not supplier_id:
            raise ValueError("Please provide valid Supplier ID")
        supplier = SupplierAdministration.objects.filter(id=supplier_id).last()
        if not supplier:
            raise ValueError("No Supplier found with this ID")
        supplier = SupplierInfoSerializer(supplier).data
        return HttpResponse(json.dumps({"result": supplier}))
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)
