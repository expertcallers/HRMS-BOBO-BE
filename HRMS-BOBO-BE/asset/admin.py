from django.contrib import admin
from .models import Asset, AssetCategory, AssetAllocation


class AssetInfo(admin.ModelAdmin):
    list_display = ['asset_category', 'serial_number', 'created_by']
    search_fields = ['asset_category', 'serial_number', 'model', 'os', 'configuration', 'created_by']
    autocomplete_fields = ['asset_category', 'created_by']


class AssetCategoryInfo(admin.ModelAdmin):
    list_display = ['name', 'created_by']
    search_fields = ['name', 'created_by']
    autocomplete_fields = ['created_by']


class AssetAllocationInfo(admin.ModelAdmin):
    list_display = ['asset', 'assigned_to', 'status', 'assigned_by', 'assigned_at']
    search_fields = ['asset', 'assigned_to', 'status', 'assigned_by', 'assigned_at']
    autocomplete_fields = ['asset', 'assigned_to', 'assigned_by']


admin.site.register(Asset, AssetInfo)
admin.site.register(AssetCategory, AssetCategoryInfo)
admin.site.register(AssetAllocation, AssetAllocationInfo)
