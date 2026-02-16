from django.urls import path
from . import views

urlpatterns = [
    path('create_asset', views.create_asset, name="create_asset"),
    path('create_asset_category', views.create_asset_category, name="create_asset_category"),
    path('get_all_assets', views.GetAllAsset.as_view(), name="get_all_assets"),
    path('get_all_asset_category', views.get_all_asset_category),
    path('update_asset/<int:asset_id>', views.update_asset, name="update_asset"),
    path('issue_asset/<int:asset_id>', views.issue_asset, name="issue_asset"),
    path('get_asset_history/<int:asset_id>', views.GetAllAssetHistory.as_view(), name="get_asset_history"),
    path('change_asset_status/<int:asset_id>', views.change_asset_status, name='change_asset_status'),
    path('return_asset/<int:asset_id>', views.return_asset, name='return_asset'),
    path('get_all_asset_allocation', views.GetAllAssetAllocation.as_view(), name="get_all_asset_allocation"),
    path('document/<str:doc_id>', views.get_document),
]
