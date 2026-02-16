from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from team.models import Team, Process


class TeamResource(resources.ModelResource):
    class Meta:
        model = Team


class TeamInfo(ImportExportModelAdmin):
    search_fields = ("id", "name", "manager__emp_id", "created_by__emp_id", "base_team__name", "updated_by__emp_id")
    list_display = ["id", "name", "base_team", "manager", "created_by", "updated_by", "created_at", "updated_at"]
    autocomplete_fields = ("manager", "base_team", "created_by", "updated_by")
    resource_class = TeamResource


class ProcessResource(resources.ModelResource):
    class Meta:
        model = Process


class ProcessInfo(ImportExportModelAdmin):
    search_fields = ("id", "name", "department__name", "created_by__emp_id")
    list_display = ["id", "name", "department", "is_active", "created_by", "created_at", "updated_at"]
    autocomplete_fields = ("department", "created_by")
    resource_class = ProcessResource


admin.site.register(Process, ProcessInfo)
admin.site.register(Team, TeamInfo)
