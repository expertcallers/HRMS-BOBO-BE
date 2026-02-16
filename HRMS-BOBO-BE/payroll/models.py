from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models

from hrms import settings
from interview.models import Candidate
from mapping.models import Profile
from utils.utils import EncryptedCField, logger, validate_alphanumeric, validate_ifsc, validate_bnk_account_no


def validate_year(val):
    today = datetime.today()
    if val < today.year and today.month != 1:
        raise ValidationError("Year must be same or greater than current year")


def validate_month(val):
    if val not in range(1, 13):
        raise ValidationError("Month must be in the range of 1 to 12")


def validate_positive_value(value):
    if not value >= 0:
        raise ValueError("Variable Pay should contain positive values")


class VariablePay(models.Model):
    emp_id = models.CharField(max_length=10)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="variable_pay_profile", blank=True,
                                null=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name="variable_pay_created_by_profile",
                                   blank=True, null=True)
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name="variable_pay_updated_by_profile",
                                   blank=True, null=True)
    comment = models.CharField(max_length=400)
    process_incentive = models.FloatField(validators=[validate_positive_value], default=0)
    client_incentive = models.FloatField(validators=[validate_positive_value], default=0)
    bb_rent = models.FloatField(validators=[validate_positive_value], default=0)
    overtime = models.FloatField(validators=[validate_positive_value], default=0)
    night_shift_allowance = models.FloatField(validators=[validate_positive_value], default=0)
    # referral = models.IntegerField(default=0)
    arrears = models.FloatField(validators=[validate_positive_value], default=0)
    attendance_bonus = models.FloatField(validators=[validate_positive_value], default=0)
    year = models.IntegerField(validators=[validate_year], blank=True, null=True)
    month = models.IntegerField(validators=[validate_month], blank=True, null=True)
    is_active = models.BooleanField(default=True)
    total = models.FloatField(default=0)
    status = models.CharField(max_length=8, choices=settings.ERF_APPROVAL_STATUS, default="Approved")  # TODO
    app_or_reg_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name="variable_pay_approved_by",
                                      blank=True, null=True)
    app_or_reg_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.profile)


class Deduction(models.Model):
    emp_id = models.CharField(max_length=10)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="deduction_profile", blank=True,
                                null=True)
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="deduction_created_by_profile",
                                   blank=True, null=True)
    updated_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="deduction_updated_by_profile",
                                   blank=True, null=True)
    tds = models.IntegerField(default=0)
    health_insurance_deduction = models.IntegerField(default=0)
    sodexo_deduction = models.IntegerField(default=0)
    cab_deduction = models.IntegerField(default=0)
    other_deduction = models.IntegerField(default=0)
    notice_period_recovery = models.IntegerField(default=0)
    year = models.IntegerField(validators=[validate_year], blank=True, null=True)
    month = models.IntegerField(validators=[validate_month], blank=True, null=True)
    is_always = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.profile)


class Salary(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, related_name="candidate_salary", blank=True,
                                  null=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                related_name="salary_linked_profile")

    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="salary_updated_by_profile")
    pay_grade = models.CharField(max_length=2, choices=settings.PAY_GRADE_LEVELS)
    last_update_reason = models.CharField(max_length=100, choices=settings.SALARY_UPDATE_REASON)
    opting_for_pf = models.BooleanField(default=False)
    pf_emp = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    pf_emr = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    basic = EncryptedCField(max_length=26, default=0)
    hra = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    oa = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    ta = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    tel_allowance = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    tds = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    medical_allowance = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    health_insurance_deduction = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    pt = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    total_fixed_gross = EncryptedCField(max_length=26, default=0)
    esi = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    esi_emr = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    ctc = EncryptedCField(max_length=26, default=0)
    net_salary = EncryptedCField(max_length=26, default=0)
    uan = models.CharField(max_length=12, blank=True, null=True)
    esic_no = models.CharField(max_length=17, blank=True, null=True)
    pf_no = models.CharField(max_length=22, blank=True, null=True)
    bank_name = EncryptedCField(max_length=255, blank=True, null=True,
                                validators=[validate_alphanumeric])
    statutory_bonus = EncryptedCField(max_length=26, default=0, blank=True, null=True)
    total_deductions = EncryptedCField(max_length=26, default=0, blank=True, null=True)

    ifsc_code = EncryptedCField(max_length=24, blank=True, null=True, validators=[validate_ifsc])
    account_number = EncryptedCField(max_length=44, unique=True, blank=True, null=True, validators=[
        validate_bnk_account_no], default=None)
    name_as_per_bank_acc = EncryptedCField(max_length=255, blank=True, null=True)
    auto_calculated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class Payroll(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="payroll_profile")
    emp_id = models.CharField(max_length=15, blank=True, null=True)
    is_processed = models.BooleanField(default=False)
    year = models.IntegerField(validators=[validate_year])
    month = models.CharField(max_length=13, blank=True, null=True)
    month_number = models.IntegerField(validators=[validate_month], blank=True, null=True)
    payment_mode = models.CharField(max_length=255, blank=True, null=True)
    pay_check = models.FloatField(default=0)
    new_qa = models.FloatField(default=0)
    branch = models.CharField(max_length=30, blank=True, null=True)
    sandwich_count = models.IntegerField(default=0)
    sandwich_dates = models.CharField(max_length=255, blank=True, null=True)

    emp_name = models.CharField(max_length=255, blank=True, null=True)
    doj = models.DateField(blank=True, null=True)
    lwd = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=30, blank=True, null=True)
    process = models.CharField(max_length=255, blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    name_as_per_bank_acc = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=30, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11, blank=True, null=True)
    pay_grade = models.CharField(max_length=3, blank=True, null=True)
    da = models.FloatField(default=0)
    new_da = models.FloatField(default=0)
    uan = models.CharField(max_length=30, blank=True, null=True)
    pf_no = models.CharField(max_length=30, blank=True, null=True)
    esic_no = models.CharField(max_length=30, blank=True, null=True)

    present = models.FloatField(default=0)
    wo = models.FloatField(default=0)

    el = models.FloatField(default=0)
    sl = models.FloatField(default=0)

    cl = models.FloatField(default=0)
    ml = models.FloatField(default=0)
    co = models.FloatField(default=0)
    trng = models.FloatField(default=0)
    hd = models.FloatField(default=0)
    nh = models.FloatField(default=0)
    absent = models.FloatField(default=0)
    att = models.FloatField(default=0)
    # new ones
    ncns = models.FloatField(default=0)
    off = models.FloatField(default=0)
    lop = models.FloatField(default=0)
    na = models.FloatField(default=0)
    other_allowances = models.FloatField(default=0)
    ctc = models.FloatField(default=0)
    is_check = models.BooleanField(default=False)
    hold_salary = models.FloatField(default=0)
    second_slot = models.BooleanField(default=False)
    p = models.FloatField(default=0)
    hd = models.FloatField(default=0)
    
    paid_days = models.FloatField(default=0)
    calendar_days = models.FloatField(default=0)
    total_days = models.FloatField(default=0)
    lop_days = models.FloatField(default=0)
    fixed_gross = models.FloatField(default=0)
    basic = models.FloatField(default=0)
    ta = models.FloatField(default=0)
    hra = models.FloatField(default=0)
    oa = models.FloatField(default=0)
    tel_allowance = models.FloatField(default=0)
    medical_allowance = models.FloatField(default=0)
    total_fixed_gross = models.FloatField(default=0)
    b_plus_d = models.FloatField(default=0)
    el_accrual = models.FloatField(default=0)
    new_basic_salary = models.FloatField(default=0)
    new_oa = models.FloatField(default=0)
    new_ta = models.FloatField(default=0)
    new_hra = models.FloatField(default=0)
    new_medical_a = models.FloatField(default=0)
    pf_gross = models.FloatField(default=0)
    statutory_bonus = models.FloatField(default=0)
    variable_pay = models.FloatField(default=0, blank=True, null=True)
    process_incentive = models.FloatField(default=0)
    client_incentive = models.FloatField(default=0)
    bb_rent = models.FloatField(default=0)
    overtime = models.FloatField(default=0)
    night_shift_allowance = models.FloatField(default=0)
    referral = models.FloatField(default=0)
    arrears = models.FloatField(default=0)
    attendance_bonus = models.FloatField(default=0)
    total_gross_salary = models.FloatField(default=0)
    pf_emp = models.FloatField(default=0)
    pf_emr = models.FloatField(default=0)
    esi = models.FloatField(default=0)
    pt = models.FloatField(default=0)
    tds = models.FloatField(default=0)
    health_insurance_deduction = models.FloatField(default=0)
    sodexo_deduction = models.FloatField(default=0)
    cab_deduction = models.FloatField(default=0)
    other_deduction = models.FloatField(default=0)
    notice_period_recovery = models.FloatField(default=0)
    total_ded = models.FloatField(default=0)
    net_salary = models.FloatField(default=0)
    welfare_fund = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.profile)


class UpdateSalaryHistory(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, related_name="update_cand_salary", blank=True,
                                  null=True)
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="update_sal_profile")
    field_updated = models.CharField(max_length=1500)
    from_data = models.CharField(max_length=1500, null=True, blank=True)
    to_data = models.CharField(max_length=1500, null=True, blank=True)
    comment = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="update_sal_updated_by")
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.profile)


class PayGrade(models.Model):
    level = models.CharField(max_length=2, unique=True, choices=settings.PAY_GRADE_LEVELS)
    basic_perc = models.IntegerField(default=40)
    hra_basic_perc = models.IntegerField(default=40)
    da_perc = models.IntegerField(default=0)
    pf_emp_perc = models.IntegerField(default=12)
    pf_emr_perc = models.IntegerField(default=12)
    tds_perc = models.IntegerField(default=0)
    travel_allow = models.IntegerField(default=0)
    telephone_allow = models.IntegerField(default=0)
    medical_allow = models.IntegerField(default=0)
    health_insurance = models.IntegerField(default=0)
    pt = models.IntegerField(default=200)

    def __str__(self):
        return str(self.level)
