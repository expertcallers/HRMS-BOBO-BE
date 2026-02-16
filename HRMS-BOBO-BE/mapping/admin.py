from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext as _
import logging
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field

from mapping.models import Profile, Department, Designation, Miscellaneous, HrmsPermissionGroup, HrmsPermission, \
    Category, ExceptionLog, EmployeeReferral, MiscellaneousMiniFields, HrmsDeptPermissionGroup, Mapping, \
    UpdateEmployeeHistory, Other, EmployeePermissions, MappedTeams, MappedTeamsHistory, ReplaceManager, \
    PermissionsToBeRemoved, LoginOtp
from utils.utils import get_column_names_with_foreign_keys_separate

logger = logging.getLogger(__name__)

# TODO workout on duplicate fields first_name,middle_name, last_name, email


from mapping.models import Migration


@admin.register(Migration)
class MigrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'app', 'name', 'applied')  # Fields to display in the admin list view
    list_filter = ('app',)  # Add a filter by app
    search_fields = ('name',)  # Enable searching by migration name
    ordering = ('-applied',)  # Show the latest migrations first


class ProfileResource(resources.ModelResource):
    # Define the fields you want to export
    source = Field()
    source_ref = Field()

    class Meta:
        model = Profile  # Replace with the actual model you are working with, e.g. User or Profile
        fields = (
            'id', 'username', 'email', 'first_name', 'middle_name', 'last_name','full_name', 'designation', 'status', 'emp_id',
            'onboard', 'is_password_changed', 'date_of_joining', 'policy_accepted', 'otp_secret', 'source',
            'source_ref',
            'team', 'sudo_team', 'my_team', 'location','dob','last_working_day','updated_by','is_active'
        )

    def dehydrate_source(self, user):
        # Method to extract the `source` field value
        return user.onboard.candidate.current_application.source if user.onboard and user.onboard.candidate and user.onboard.candidate.current_application else None

    def dehydrate_source_ref(self, user):
        # Method to extract the `source_ref` field value
        return user.onboard.candidate.current_application.source_ref if user.onboard and user.onboard.candidate and user.onboard.candidate.current_application else None


class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    ordering = ['id']
    list_display = ['id', "last_activity_at", 'username', "interview", "is_active", "email", "onboard", "dob",
                    "full_name", "status", "emp_id", "first_name", "rm1", "rm1_name", "rm2", "rm2_name", "rm3",
                    "rm3_name", 'middle_name', "last_name", "sudo_team", "sudo_team_name", "team", "team_name",
                    'department', 'designation', 'is_password_changed', "date_of_joining", "updated_by", "created_at",
                    'updated_at', "last_working_day", "policy_accepted", "source", "source_ref"]
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': (
            'email', 'password', 'designation', "status", 'image', 'emp_id', 'onboard',
            'is_password_changed', "my_team", "sudo_team", "team", "username", "dob", "full_name", "updated_by","last_working_day",
            "date_of_joining", "policy_accepted", "otp_secret")}),
        (_('Personal Info'), {'fields': ('first_name', 'middle_name', 'last_name',)}),
        (
            _('Permissions'),
            {'fields': ('is_active', 'is_staff', 'is_superuser')}
        ),
        (_('Important dates'), {'fields': ('last_login',)})
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'password1', 'password2', 'first_name', 'middle_name', 'last_name', 'username', 'emp_id', 'onboard',
                'designation', 'image', "sudo_team", "status", 'email', 'team', 'my_team',
                'is_password_changed', "date_of_joining", "policy_accepted", "otp_secret")
        }),
    )
    search_fields = (
        'id', 'username', 'email', 'first_name', "designation__category__name", "designation__name", 'middle_name',
        'last_name', "status", "sudo_team__name", "team__name", "full_name")
    autocomplete_fields = ["onboard", "designation", "sudo_team", "team", "my_team", "erf", "updated_by"]
    resource_class = ProfileResource

    def department(self, obj):
        return obj.designation.department.name if obj.designation and obj.designation.department else None

    def team_name(self, obj):
        return obj.team.name if obj.team else None

    def sudo_team_name(self, obj):
        return obj.sudo_team.name if obj.sudo_team else None

    def source(self, obj):
        return obj.onboard.candidate.current_application.source if obj.onboard and obj.onboard.candidate and obj.onboard.candidate.current_application else None

    def source_ref(self, obj):
        return obj.onboard.candidate.current_application.source_ref if obj.onboard and obj.onboard.candidate and obj.onboard.candidate.current_application else None

    def rm1(self, obj):
        return obj.team.manager.emp_id if obj.team and obj.team.manager else None

    def rm2(self, obj):
        return obj.team.manager.team.manager.emp_id if self.rm1(
            obj) and obj.team.manager.team and obj.team.manager.team.manager else None

    def rm3(self, obj):
        return obj.team.manager.team.manager.team.manager.emp_id if self.rm2(
            obj) and obj.team.manager.team.manager.team and obj.team.manager.team.manager.team.manager else None

    def rm1_name(self, obj):
        return obj.team.manager.full_name if obj.team and obj.team.manager else None

    def rm2_name(self, obj):
        return obj.team.manager.team.manager.full_name if self.rm1(
            obj) and obj.team.manager.team and obj.team.manager.team.manager else None

    def rm3_name(self, obj):
        return obj.team.manager.team.manager.team.manager.full_name if self.rm2(
            obj) and obj.team.manager.team.manager.team and obj.team.manager.team.manager.team.manager else None


def change_category_to_AM(modeladmin, request, queryset):
    category = Category.objects.get(name="AM")
    queryset.update(category=category)


class DepartmentResource(resources.ModelResource):
    class Meta:
        model = Department


class DepartmentInfo(ImportExportModelAdmin):
    search_fields = ('id', 'name', 'created_by', 'created_at', 'updated_at')
    list_display = ['id', 'dept_id', 'name', 'created_by', 'created_at', 'updated_at']
    resource_class = DepartmentResource


class DesignationResource(resources.ModelResource):
    class Meta:
        model = Designation


class DesignationInfo(ImportExportModelAdmin):
    search_fields = ('id', "name", 'created_by', "category__name", 'created_at', 'updated_at')
    list_display = ['id', "name", "department", "category", 'created_by', 'created_at', 'updated_at']
    resource_class = DesignationResource
    # actions = [change_category_to_AM]


class MiscellaneousInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Miscellaneous)
    search_fields = list_display.copy()
    list_display += foreign_keys


class MiscellaneousMiniFieldsInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        MiscellaneousMiniFields)
    search_fields = list_display.copy()
    list_display += foreign_keys


class HrmsPermissionGroupResource(resources.ModelResource):
    class Meta:
        model = HrmsPermissionGroup


class HrmsGroupAdmin(ImportExportModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)
    list_display = ['id', 'name']
    autocomplete_fields = ["category"]
    resource_class = HrmsPermissionGroupResource


class HrmsDeptPermissionGroupResource(resources.ModelResource):
    class Meta:
        model = HrmsDeptPermissionGroup


class HrmsEmpPermissionResource(resources.ModelResource):
    class Meta:
        model = EmployeePermissions


class HrmsEmployeePermissionAdmin(ImportExportModelAdmin):
    search_fields = ("profile__emp_id", "id")
    ordering = ("id",)
    filter_horizontal = ("permissions",)
    list_display = ['id', 'profile', "name"]
    autocomplete_fields = ["profile"]
    resource_class = HrmsEmpPermissionResource

    def name(self, obj):
        return obj.profile.full_name


class HrmsPermissionResource(resources.ModelResource):
    class Meta:
        model = HrmsPermission


class HrmsDeptPermissionGroupAdmin(ImportExportModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)
    list_display = ['id', 'name', 'department']
    autocomplete_fields = ["department"]
    resource_class = HrmsDeptPermissionGroupResource


class PermissionsToBeRemovedResource(resources.ModelResource):
    class Meta:
        model = PermissionsToBeRemoved


class PermissionsToBeRemovedInfo(ImportExportModelAdmin):
    search_fields = ("id",)
    ordering = ("id",)
    filter_horizontal = ("permissions",)
    list_display = ['id']
    resource_class = PermissionsToBeRemovedResource


class HrmsPermissionAdmin(ImportExportModelAdmin):
    search_fields = ("id", "module_name")
    list_display = ['id', 'url_name', 'url_route', 'module_name']
    resource_class = HrmsPermissionResource


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category


class CategoryInfo(ImportExportModelAdmin):
    search_fields = ('name',)
    list_display = ['id', 'name', 'created_by']
    resource_class = CategoryResource


class ExceptionLogInfo(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'message']


class EmployeeReferenceInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(EmployeeReferral)
    search_fields = list_display.copy()
    list_display += foreign_keys


class MappingInfo(admin.ModelAdmin):
    search_fields = ["status", "id", "employee__emp_id", "from_team__name", "to_team__name"]
    list_display = ["id", "employee", "status", "is_open", "created_by", "to_team", "from_team", "approved_by",
                    "mapped_teams", "created_at", "updated_at"]
    autocomplete_fields = ["employee", "from_team", "to_team", "mapped_teams", "approved_by"]


class OtherResource(resources.ModelResource):
    class Meta:
        model = Other


class OtherInfo(ImportExportModelAdmin):
    list_display = ["emp_id", "char_field", "bool_field", "datetime_field"]
    search_fields = ["emp_id", "char_field", "bool_field", "datetime_field"]
    resource_class = OtherResource


class UpdateEmployeeHistoryResource(resources.ModelResource):
    class Meta:
        model = UpdateEmployeeHistory


class UpdateEmployeeHistoryInfo(ImportExportModelAdmin):
    list_display = ["id", "profile", "field_updated", "from_data", "to_data", "comment", "updated_by", "updated_at"]
    search_fields = ["profile__emp_id", "field_updated", "comment", "updated_by__emp_id", "updated_at"]
    autocomplete_fields = ["profile", "updated_by"]
    resource_class = UpdateEmployeeHistoryResource


class MappedTeamsResource(resources.ModelResource):
    class Meta:
        model = MappedTeams


class MappedTeamsInfo(ImportExportModelAdmin):
    list_display = ["id", "from_employee", "to_employee", "replaced_employee", "replaced_by", "reason",
                    "replacement_reason", 'created_at', 'updated_at']
    search_fields = ("id", "from_employee__emp_id", "to_employee__emp_id", "replaced_employee__emp_id")
    autocomplete_fields = ("from_employee", "to_employee", "replaced_employee", "replaced_by", "mapped_teams")
    resource_class = MappedTeamsResource


# class MappedTeamsHistory(models.Model):
#     mapped_teams = models.ForeignKey(MappedTeams, on_delete=models.CASCADE, related_name="mapped_teams_history")
#     replaced_employee = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
#                                           related_name="replaced_employee_history")
#     replaced_by = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
#                                     related_name="replaced_by_employee_history")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

class MappedTeamsHistoryResource(resources.ModelResource):
    class Meta:
        model = MappedTeamsHistory


class MappedTeamsHistoryInfo(ImportExportModelAdmin):
    list_display = ["id", "replaced_employee", "replaced_by", "created_at", "updated_at"]
    search_fields = ("replaced_employee__emp_id", "replaced_by__emp_id", "created_at")
    autocomplete_fields = ["replaced_employee", "replaced_by"]
    resource_class = MappedTeamsResource


class ReplaceManagerInfo(admin.ModelAdmin):
    list_display = ["id", "team", "created_by", "created_by_name", "new_manager", "new_mgr_name", "old_manager",
                    "old_mgr_name", "department", "process", "created_at", "updated_at", "comment"]
    search_fields = ("old_manager__emp_id", "new_manager__emp_id", "team__name", "created_at")
    autocomplete_fields = ["old_manager", "new_manager", "team", "created_by"]

    def department(self, obj):
        return obj.team.base_team.department.name if obj.team and obj.team.base_team and obj.team.base_team.department else None

    def process(self, obj):
        return obj.team.base_team.name if obj.team and obj.team.base_team else None

    def created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None

    def old_mgr_name(self, obj):
        return obj.old_manager.full_name if obj.old_manager else None

    def new_mgr_name(self, obj):
        return obj.new_manager.full_name if obj.new_manager else None


class LoginOtpInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(LoginOtp)
    search_fields = list_display.copy()
    list_display += foreign_keys


admin.site.register(LoginOtp, LoginOtpInfo)
admin.site.register(PermissionsToBeRemoved, PermissionsToBeRemovedInfo)
admin.site.register(Mapping, MappingInfo)
admin.site.register(HrmsDeptPermissionGroup, HrmsDeptPermissionGroupAdmin)
admin.site.register(EmployeeReferral, EmployeeReferenceInfo)
admin.site.register(ExceptionLog, ExceptionLogInfo)
admin.site.register(Category, CategoryInfo)
admin.site.register(HrmsPermission, HrmsPermissionAdmin)
admin.site.register(HrmsPermissionGroup, HrmsGroupAdmin)
admin.site.register(Profile, UserAdmin)
admin.site.register(Department, DepartmentInfo)
admin.site.register(Designation, DesignationInfo)
admin.site.register(Miscellaneous, MiscellaneousInfo)
admin.site.register(MiscellaneousMiniFields, MiscellaneousMiniFieldsInfo)
admin.site.register(UpdateEmployeeHistory, UpdateEmployeeHistoryInfo)
admin.site.register(Other, OtherInfo)
admin.site.register(EmployeePermissions, HrmsEmployeePermissionAdmin)
admin.site.register(MappedTeams, MappedTeamsInfo)
admin.site.register(ReplaceManager, ReplaceManagerInfo)
admin.site.register(MappedTeamsHistory, MappedTeamsHistoryInfo)
