from datetime import datetime

from django.db import models
from rest_framework.exceptions import ValidationError

from hrms import settings
from mapping.models import Profile

# Create your models here.
ATTENDANCE_STATUS = settings.ATTENDANCE_STATUS
MARK_ATTENDANCE_STATUS = settings.MARK_ATTENDANCE_STATUS
LEAVE_STATUS = settings.LEAVE_STATUS
LEAVE_TYPES = settings.LEAVE_TYPES


def validate_mark_attendance_status(val):
    if val == "Scheduled":
        raise ValidationError("You cannot set status as Scheduled")


def validate_date(val):
    if val < datetime.today().date():
        return ValidationError("Date must be current day or future day")


def validate_attendance_date(val):
    pass
    # if val > datetime.today().date():
    #     raise ValidationError("date cannot be future date.")


class Schedule(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="schedule_attendance_profile")
    emp_id = models.CharField(max_length=16, blank=True, null=True)
    rm1_id = models.CharField(max_length=16, blank=True, null=True)
    created_by_emp_id = models.CharField(max_length=16, blank=True, null=True)
    create_type = models.CharField(max_length=3,
                                   choices=[("MSC", "MSC"), ("CCU", "CCU"), ("GEN", "GEN"), ("PC", "PC")], blank=True,
                                   null=True)  # MSC(Missing Schedule Creation) # CC Update, GENERAL, PROFILE CREATION
    start_date = models.DateField(validators=[validate_attendance_date])
    end_date = models.DateField(validators=[validate_attendance_date])
    start_time = models.TimeField()
    end_time = models.TimeField()
    week_off = models.CharField(max_length=65, blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True)
    is_training = models.BooleanField(default=False)
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="schedule_att_profile_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.profile)


class Attendance(models.Model):
    status = models.CharField(choices=ATTENDANCE_STATUS, max_length=11, db_index=True)
    logged_in_ip = models.CharField(max_length=16, blank=True, null=True)
    date = models.DateField(validators=[validate_attendance_date], db_index=True)
    start_time = models.CharField(max_length=8, default="00:00:00", db_index=True)
    end_time = models.CharField(max_length=8, default="00:00:00", db_index=True)
    emp_start_time = models.DateTimeField(blank=True, null=True, db_index=True)
    emp_end_time = models.DateTimeField(blank=True, null=True, db_index=True)
    total_time = models.CharField(max_length=12, blank=True, null=True, db_index=True)
    is_training = models.BooleanField(default=False, db_index=True)
    sch_upd_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="schedule_updated_by", db_index=True)
    is_sandwich = models.BooleanField(default=False)
    over_time = models.FloatField(default=0)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="attendance_profile", db_index=True)
    is_self_marked = models.BooleanField(default=False, db_index=True)
    approved_at = models.DateTimeField(blank=True, null=True, db_index=True)
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="attapprby",
                                    db_index=True)
    is_auto_approved = models.BooleanField(default=False)
    is_att_cor_req = models.BooleanField(default=False, db_index=True)
    comment = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    logged_out_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name="logged_out_by", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return str(self.profile)


class SuspiciousLoginActivity(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="susloginact")
    logged_in_ip = models.CharField(max_length=16, blank=True, null=True)
    activity_type = models.CharField(max_length=20, blank=True, null=True)
    other_ip_address = models.CharField(max_length=16, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return str(self.id)


class AttendanceCorrectionHistory(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="attendanceCorHist")
    correction_status = models.CharField(max_length=10, choices=settings.AMS_CORRECTION_STATUS, db_index=True)
    att_cor_req_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                       related_name="attcorreqby", db_index=True)
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="attcorrby", db_index=True)
    is_training = models.BooleanField(default=False, db_index=True)
    approved_at = models.DateTimeField(blank=True, null=True, db_index=True)
    requested_status = models.CharField(choices=ATTENDANCE_STATUS, max_length=11, db_index=True)
    approved_comment = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    request_comment = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.attendance)


class Events(models.Model):
    title = models.CharField(max_length=225)
    start_date = models.DateTimeField()  # actual day of the event
    end_date = models.DateTimeField()
    all_day = models.BooleanField(default=False)

    def __str__(self):
        return str(self.start_date)


class LeaveBalance(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="emp_leave_balance")
    sick_leaves = models.FloatField(default=0)
    paid_leaves = models.FloatField(default=0)
    total = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    # current_year = models.CharField(max_length=4, validators=[validate_year]) #TODO update new_year policy based on the current_year

    def __str__(self):
        return str(self.profile)


class MonthlyLeaveBalance(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="emp_monthly_leave_balance")
    date = models.DateTimeField(auto_now_add=True)
    leave_type = models.CharField(max_length=30)
    transaction = models.CharField(max_length=300)
    no_of_days = models.FloatField()
    total = models.FloatField(null=True, blank=True)

    def __str__(self):
        return str(self.profile)


class LeaveBalanceHistory(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="emp_leave_balance_history")
    date = models.DateTimeField(auto_now_add=True)
    leave_type = models.CharField(max_length=30)
    transaction = models.CharField(max_length=300)
    no_of_days = models.FloatField()
    sl_balance = models.FloatField(null=True, blank=True)
    pl_balance = models.FloatField(null=True, blank=True)
    total = models.FloatField(null=True, blank=True)

    def __str__(self):
        return str(self.profile)


class Leave(models.Model):
    start_date = models.DateField(validators=[validate_date])
    end_date = models.DateField(validators=[validate_date])
    applied_on = models.DateTimeField(auto_now_add=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile_leave")
    no_of_days = models.IntegerField()
    reason = models.CharField(max_length=255)
    leave_type = models.CharField(choices=LEAVE_TYPES, max_length=10)
    tl_status = models.CharField(choices=LEAVE_STATUS, max_length=11, default="Pending")
    tl_comments = models.CharField(max_length=255, blank=True, null=True)
    manager_status = models.CharField(choices=LEAVE_STATUS, max_length=11, default="Pending")
    manager_comments = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(choices=LEAVE_STATUS, max_length=11, default="Pending")
    escalate = models.BooleanField(default=False)
    escalate_comment = models.CharField(max_length=255, blank=True, null=True)
    approved_by1 = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name="approved_by1")
    approved_by2 = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name="approved_by2")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.profile)


class Break(models.Model):
    comment = models.CharField(max_length=255, null=True, blank=True)
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="break_profile")
    attendance = models.ForeignKey(Attendance, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="break_attendance")
    break_type = models.CharField(max_length=255)
    break_start_time = models.DateTimeField()
    break_end_time = models.DateTimeField(null=True, blank=True)
    total_time = models.CharField(max_length=12, blank=True, null=True)

    def __str__(self):
        return str(self.profile)


class AttendanceLog(models.Model):
    user_id = models.CharField(max_length=50)
    user_name = models.CharField(max_length=100, null=True, blank=True)  # ✅ Add this
    timestamp = models.DateTimeField()
    status = models.IntegerField()
    device_ip = models.GenericIPAddressField()
    entry_type = models.CharField(max_length=5)

    class Meta:
        unique_together = ('user_id', 'timestamp', 'device_ip')