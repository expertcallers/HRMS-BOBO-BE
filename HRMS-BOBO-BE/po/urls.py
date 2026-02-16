from django.urls import path
from po import views

urlpatterns = [
    path('create_po', views.create_po, name='create_po'),
    path('create_supplier', views.create_supplier, name='create_supplier'),
    path('get_all_supplier', views.get_all_supplier),
    path('get_all_supplier_info', views.GetAllSupplierInfo.as_view(), name='get_all_supplier_info'),
    path('get_all_po_info', views.GetAllPOInfo.as_view(), name="get_all_po_info"),
    path('update_po/<int:po_id>', views.update_po, name='update_po'),
    path('update_supplier/<int:supplier_id>', views.update_supplier, name='update_supplier'),
    path('get_supplier_info/<int:supplier_id>', views.get_supplier_info),
]
