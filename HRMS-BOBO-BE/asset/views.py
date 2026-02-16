from django.http import HttpResponse
import json
import logging
from rest_framework import status
from datetime import datetime
from mapping.views import HasUrlPermission
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from utils.util_classes import CustomTokenAuthentication
from .serializers import AssetSerializer, AssetCategorySerializer, UpdateAssetSerializer, AssetHistorySerializer, \
    AssetAllocationSerializer, ViewAssetAllocationSerializer, UpdateAssetStatusSerializer
from .models import Asset, AssetCategory, AssetHistory, Document, AssetAllocation
from mapping.models import Profile
from utils.utils import update_request, return_error_response, get_sort_and_filter_by_cols, get_formatted_name, \
    document_response
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


def get_asset_by_id(asset_id):
    if asset_id is None:
        raise ValueError("Provide valid ID")
    try:
        asset_obj = Asset.objects.get(id=asset_id)
    except:
        raise ValueError("Asset with this ID doesn't exist.")
    return asset_obj


def create_file(field, file, user=None):
    emp_id = user.emp_id if user else None
    name = get_formatted_name(user) if user else None
    document = Document(field=field, file=file, uploaded_by_emp_id=emp_id, uploaded_by_name=name, file_name=file.name)
    return document


def create_asset_history(asset, trans, msg, usr):
    AssetHistory.objects.create(asset=asset, transaction=trans, message=msg, created_by=usr, created_at=datetime.now())
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def get_document(request, doc_id):
    return document_response(Document, doc_id)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_asset(request):
    try:
        category = request.data.get("asset_category")
        category, is_new = AssetCategory.objects.get_or_create(name=category)
        if is_new:
            category.created_by = request.user
            category.save()
        data = update_request(request.data, created_by=request.user.id, asset_category=category.id, status="Available")
        serializer = AssetSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        asset = serializer.create(serializer.validated_data)
        create_asset_history(asset, trans="Asset Created",
                             msg="New Asset '{0}' added to Inventory by {1} at {2}".format(asset.asset_category,
                                                                                           get_formatted_name(
                                                                                               request.user),
                                                                                           datetime.now()),
                             usr=request.user)
        return HttpResponse(json.dumps({"message": "Asset created successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_asset_category(request):
    try:
        data = update_request(request.data, created_by=request.user.id)
        serializer = AssetCategorySerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        asset_category = serializer.create(serializer.validated_data)
        return HttpResponse(json.dumps({"message": "New Asset category added successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllAsset(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = AssetSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"asset_category": "asset_category__name", "created_by_emp_id": "created_by__emp_id",
                          "created_by_name": "created_by__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Asset.objects.filter(search_query).filter(
            **filter_by).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_asset_category(request):
    try:
        search = request.data.get("name")
        category = []
        if search:
            category = list(AssetCategory.objects.filter(name__icontains=search).values_list("name", flat=True))
        return HttpResponse(json.dumps({"result": category}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_asset(request, asset_id):
    try:
        asset = get_asset_by_id(asset_id)
        data = update_request(request.data)
        serializer_class = UpdateAssetSerializer(data=data, partial=True)
        if not serializer_class.is_valid():
            return_error_response(serializer_class, raise_exception=True)
        serializer_class.update(asset, serializer_class.validated_data)
        create_asset_history(asset, trans="Asset Updated",
                             msg="Asset updated in Inventory by {0} at {1}".format(get_formatted_name(request.user),
                                                                                   datetime.now()),
                             usr=request.user)
        return HttpResponse(json.dumps({"message": "Asset updated successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def issue_asset(request, asset_id):
    try:
        asset_docs = []
        asset = get_asset_by_id(asset_id)
        assigned_to_emp_id = request.data.get("assigned_to")
        if not assigned_to_emp_id:
            raise ValueError("Provide valid Emp ID of Employee")
        assigned_to = Profile.objects.filter(emp_id=assigned_to_emp_id)
        if not assigned_to:
            raise ValueError("User with {0} emp_id doesn't exist".format(assigned_to_emp_id))
        data = update_request(request.data, asset=asset.id, assigned_by=request.user.id,
                              assigned_to=assigned_to.last().id)
        serializer = AssetAllocationSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["status"] = "Issued"
        files = request.FILES.getlist('docs')
        if files and type(files) == list:
            for i in files:
                document = create_file('asset_docs', i, user=request.user)
                if document:
                    asset_docs.append(document)
        allocation = serializer.create(serializer.validated_data)
        if len(asset_docs) > 0:
            for doc in asset_docs:
                doc.asset_allocation_id = allocation.id
                doc.save()
                allocation.docs.add(doc)
        asset.status = "Assigned"
        asset.save()
        create_asset_history(asset, trans="Asset Issued", msg="Asset issued to {0} by {1} at {2}".format(
            get_formatted_name(serializer.validated_data["assigned_to"]), get_formatted_name(request.user),
            datetime.now()), usr=request.user)
        return HttpResponse(
            json.dumps({"message": "Asset issued to {0} successfully.".format(get_formatted_name(assigned_to.last()))}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllAssetHistory(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = AssetHistorySerializer
    model = serializer_class.Meta.model

    def get(self, request, asset_id, *args, **kwargs):
        fields_look_up = {"created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = AssetHistory.objects.filter(asset=asset_id).filter(search_query).filter(**filter_by).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def change_asset_status(request, asset_id):
    try:
        usr = request.user
        serializer = UpdateAssetStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        asset = get_asset_by_id(asset_id)
        old_status = asset.status
        if asset.status == "Assigned":
            raise ValueError("Asset status set to {0}. Archive Asset not allowed.".format(asset.status))
        new_status = serializer.validated_data["status"]
        asset.status = new_status
        asset.save()
        create_asset_history(asset, trans="Asset Status Changed",
                             msg="Asset status changed form {0} ot {1} by {2} at {3}".format(old_status, new_status,
                                                                                             get_formatted_name(
                                                                                                 request.user),
                                                                                             datetime.now()),
                             usr=request.user)
        return HttpResponse(json.dumps({"message": "Asset Status changed successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def return_asset(request, asset_id):
    try:
        data = request.data
        asset = get_asset_by_id(asset_id)
        logger.info("{0}status".format(asset.status))
        allocated = AssetAllocation.objects.filter(asset=asset, status="Issued").last()
        if not (allocated.status == "Issued"):
            raise ValueError("Asset is not Assigned to anyone.")
        allocated.status = "Returned"
        allocated.returned_at = datetime.now()
        allocated.return_comment = data.get("return_comment")
        allocated.save()
        asset.status = "Available"
        asset.save()
        create_asset_history(asset, trans="Asset Returned", msg="Asset returned by {0} at {1}".format(
            get_formatted_name(allocated.assigned_to), datetime.now()), usr=request.user)
        return HttpResponse(json.dumps({"message": "Asset Returned Successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllAssetAllocation(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = ViewAssetAllocationSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"assigned_to_emp_id": "assigned_to__emp_id", "assigned_to_name": "assigned_to__full_name",
                          "assigned_by_emp_id": "assigned_by__emp_id", "assigned_by_name": "assigned_by__full_name",
                          "serial_number": "asset__serial_number", "asset_category": "asset__asset_category"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = AssetAllocation.objects.filter(search_query).filter(**filter_by).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)
