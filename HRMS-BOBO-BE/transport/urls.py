from django.urls import path

from transport.views import CabAddressDetail

urlpatterns = [
    path('cab_address', CabAddressDetail.as_view(), name="admin_cab_address_get"),
    path('cab_address/<str:cab_address_id>', CabAddressDetail.as_view(), name="admin_cab_address_update")
]
