from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from ams.models import Attendance, Leave, LeaveBalance, LeaveBalanceHistory, AttendanceCorrectionHistory, Schedule, \
    Break, MonthlyLeaveBalance, SuspiciousLoginActivity, AttendanceLog
from utils.utils import get_column_names, get_column_names_with_foreign_keys_separate


def mark_all_present(modeladmin, request, queryset):
    queryset.update(status="Present", approved_by=request.user)


def mark_all_Unmarked(modeladmin, request, queryset):
    queryset.update(status="Scheduled", approved_by=request.user)


def mark_all_Weekoff(modeladmin, request, queryset):
    queryset.update(status="Week Off", approved_by=request.user)


def mark_all_leaves_pending(modeladmin, request, queryset):
    queryset.update(status="Pending", approved_by=request.user)


def delete_all(modeladmin, request, queryset):
    queryset.delete()


class SuspiciousLoginActivityResource(resources.ModelResource):
    class Meta:
        model = SuspiciousLoginActivity


class SuspiciousLoginActivityInfo(ImportExportModelAdmin):
    list_display, autocomplete_fields = get_column_names(SuspiciousLoginActivity)
    search_fields = ["attendance__profile__emp_id", "attendance__profile__full_name", "activity_type",
                     "attendance__profile__team__base_team__name", "attendance__profile__designation__name"]
    list_display += ["checkin", "checkout", "emp_id", "emp_name", "designation", "process"]
    list_filter = ['activity_type']
    resource_class = SuspiciousLoginActivityResource

    def total_time(self, obj):
        return obj.attendance.total_time

    def checkin(self, obj):
        return obj.attendance.emp_start_time

    def checkout(self, obj):
        return obj.attendance.emp_end_time

    def process(self, obj):
        return obj.attendance.profile.team.base_team.name

    def designation(self, obj):
        return obj.attendance.profile.designation.name

    def emp_id(self, obj):
        return obj.attendance.profile.emp_id

    def emp_name(self, obj):
        return obj.attendance.profile.full_name

class AttendanceResource(resources.ModelResource):
    class Meta:
        model = Attendance

    def dehydrate_profile(self, obj):
        return f"{obj.profile.emp_id}" if obj.profile else None

class AttendanceInfo(ImportExportModelAdmin):
    list_display = (
        "id", "is_auto_approved", "is_att_cor_req", "status", "is_training", "date", "is_sandwich", "is_self_marked",
        "created_at", "updated_at", "profile", "total_time", "start_time", "end_time", "emp_start_time", "emp_end_time",
        "profile_team_manager", "approved_by", "apprbyname", "sch_upd_by", "comment", "logged_out_by", "logged_in_ip")
    search_fields = ("status", "=profile__emp_id", "date")
    actions = [mark_all_present, mark_all_Unmarked, mark_all_Weekoff, delete_all]
    autocomplete_fields = ['profile']
    readonly_fields = ('is_self_marked',)  # Set is_self_marked as readonly
    resource_class =AttendanceResource

    fields = (
        "status", "is_auto_approved", "is_training", "date", "profile", "total_time", "start_time", "end_time",
        "sch_upd_by", "emp_start_time", "emp_end_time", "comment")

    def apprbyname(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None

    def profile_team_manager(self, obj):
        return obj.profile.team.manager.emp_id if obj.profile and obj.profile.team and obj.profile.team.manager else None

    profile_team_manager.short_description = 'manager'

    def __str__(self):
        return str(self.profile)


class LeaveInfo(admin.ModelAdmin):
    list_display = ["id", "start_date", "end_date", "applied_on", "updated_at", "no_of_days", "reason", "leave_type",
                    "tl_status", "tl_comments", "manager_status", "manager_comments", "status", "profile"]
    search_fields = ("applied_on", "reason", "leave_type", "profile__emp_id")
    actions = [mark_all_leaves_pending]
    autocomplete_fields = ['profile']


class LeaveBalanceResource(resources.ModelResource):
    class Meta:
        model = LeaveBalance


class LeaveBalanceInfo(ImportExportModelAdmin):
    list_display = ["id", "profile", "total", "sick_leaves", "paid_leaves", "updated_at"]
    search_fields = ["id", "profile__emp_id"]
    autocomplete_fields = ['profile']
    resource_class = LeaveBalanceResource


class LeaveBalanceHistoryInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(LeaveBalanceHistory)
    # search_fields = list_display.copy()
    search_fields = ["id", "profile__emp_id"]
    list_display += foreign_keys


class MonthlyLeaveBalanceResource(resources.ModelResource):
    class Meta:
        model = MonthlyLeaveBalance


class MonthlyLeaveBalanceInfo(ImportExportModelAdmin):
    list_display = ["profile", "date", "leave_type", "transaction", "no_of_days", "total","date"]
    search_fields = ("date", "profile__emp_id")
    autocomplete_fields = ["profile"]
    resource_class = MonthlyLeaveBalanceResource


class AttendanceCorrectionHistoryInfo(admin.ModelAdmin):
    list_display = ["attendance", "attendance_date", "attendance_profile", "correction_status", "att_cor_req_by",
                    "approved_by", "approved_at", "requested_status", "request_comment", "created_at", "updated_at"]
    search_fields = ("attendance__profile__emp_id", "id")
    autocomplete_fields = ("attendance", "att_cor_req_by", "approved_by")

    def attendance_profile(self, obj):
        return obj.attendance.profile

    def attendance_date(self, obj):
        return obj.attendance.date


class ScheduleInfo(admin.ModelAdmin):
    list_display = ["id", "profile", "emp_id", "rm1_id", "created_by_emp_id", "created_at", "start_date", "end_date",
                    "start_time", "end_time", 'week_off', "create_type", "comment"]
    search_fields = ["profile__emp_id", "id"]
    autocomplete_fields = ("profile",)

class BreakResource(resources.ModelResource):
    class Meta:
        model = Break

    def dehydrate_profile(self, obj):
        return f"{obj.profile.emp_id}" if obj.profile else None

class BreakInfo(ImportExportModelAdmin):
    list_display = ["id", "comment", "profile", "attendance", "break_type", "break_start_time", 'break_end_time',
                    "total_time"]
    search_fields = ["id", "comment", "break_type", "break_start_time", 'break_end_time', "profile__emp_id"]
    autocomplete_fields = ["profile", "attendance"]
    list_filter = ["break_start_time", "break_end_time"]  # Add this line
    resource_class = BreakResource


class AttendanceLogResource(resources.ModelResource):
    class Meta:
        model = AttendanceLog

class AttendanceLogDisplay(ImportExportModelAdmin):
    list_display = ["id","user_id","user_name", "timestamp", "status","device_ip","entry_type" ]
    search_fields=["id","user_id","user_name", "timestamp", "status","device_ip","entry_type" ]
    list_filter=["timestamp"]
    resources=AttendanceLogResource





admin.site.register(Schedule, ScheduleInfo)
admin.site.register(AttendanceCorrectionHistory, AttendanceCorrectionHistoryInfo)
admin.site.register(LeaveBalance, LeaveBalanceInfo)
admin.site.register(LeaveBalanceHistory, LeaveBalanceHistoryInfo)
admin.site.register(MonthlyLeaveBalance, MonthlyLeaveBalanceInfo)
admin.site.register(Attendance, AttendanceInfo)
admin.site.register(Leave, LeaveInfo)
admin.site.register(Break, BreakInfo)
admin.site.register(SuspiciousLoginActivity, SuspiciousLoginActivityInfo)
admin.site.register(AttendanceLog, AttendanceLogDisplay)