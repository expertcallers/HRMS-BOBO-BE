import uuid
from datetime import datetime

from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser, PermissionsMixin, AnonymousUser
from django.core.validators import validate_email
from crum import get_current_user

import logging

from hrms import settings
from utils.utils import validate_current_century, document_file

logger = logging.getLogger(__name__)
MISC_FIELD_CHOICES = settings.MISC_FIELDS
MISC_MINI_FIELDS = settings.MISC_MINI_FIELDS


def profile_file(instance, filename):
    return '/'.join(['profile', filename])


# prefer to create foreign keys to the User model importing the settings 'from django.conf import settings' and
# referring to the 'settings.AUTH_USER_MODEL' instead of referring directly to the custom User model.


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)
    dept_id = models.CharField(max_length=5, unique=True)
    allow_ticketing = models.BooleanField(default=False)
    created_by = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_by = models.CharField(max_length=20)

    def __str__(self):
        return str(self.name)


class Designation(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="desi_department")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='desi_category')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name) + " ( " + str(self.department.name) + " ) "


def validate_emp_id(value):
    value = str(value).strip()
    for i in value:
        if not str(i).isalnum() and i != "-":
            raise ValueError("emp_id cannot have special characters")


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        user = self.model(username=username, email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.emp_id = username
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Creates new superuser"""
        user = self.create_user(username, email, password, **extra_fields)
        user.is_superuser = True
        user.is_staff = True
        user.emp_id = username
        user.save(using=self._db)
        return user


class LoginOtp(models.Model):
    email = models.EmailField(validators=[validate_email])
    emp_id = models.CharField(max_length=20)
    otp = models.CharField()
    otp_datetime = models.DateTimeField()
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.emp_id)


class Profile(AbstractUser, PermissionsMixin):
    dob = models.DateField(validators=[validate_current_century], blank=True, null=True)
    middle_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=555, blank=True, null=True)
    image = models.ImageField(upload_to=profile_file, null=True, blank=True,
                              validators=[FileExtensionValidator(allowed_extensions=['webp', 'png', 'jpeg', 'jpg'])])
    email = models.EmailField(validators=[validate_email], blank=True, null=True)
    date_of_joining = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True)
    emp_id = models.CharField(max_length=20, validators=[validate_emp_id])
    status = models.CharField(max_length=30, choices=settings.PROFILE_STATUS, default="Active")
    erf = models.ForeignKey('erf.ERF', on_delete=models.SET_NULL, related_name="profile_erf", blank=True, null=True)
    onboard = models.ForeignKey('onboarding.Onboard', on_delete=models.SET_NULL, null=True,
                                related_name="profileonboard", blank=True)  # TODO discuss it
    my_team = models.ManyToManyField('team.Team', blank=True, related_name="my_team")
    team = models.ForeignKey('team.Team', on_delete=models.SET_NULL, blank=True, null=True, related_name="team")
    sudo_team = models.ForeignKey('team.Team', on_delete=models.SET_NULL, blank=True, null=True,
                                  related_name="sudo_team")
    last_working_day = models.DateField(null=True, blank=True)
    is_password_changed = models.BooleanField(default=False)
    interview = models.BooleanField(default=False)
    physically_disabled = models.BooleanField(default=False)
    specific_diseases_80ddb = models.CharField(max_length=255, blank=True, null=True)
    policy_accepted = models.BooleanField(default=True)  # HRMS user guidelines
    updated_by = models.ForeignKey("mapping.Profile", on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="pro_updated_by")
    otp_secret = models.CharField(max_length=32, blank=True, null=True)  # Store OTP secret key here
    last_totp = models.CharField(max_length=6, blank=True, null=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = UserManager()

    class Meta:
        db_table = "profile"

    def __str__(self):
        return str(self.emp_id)

    def save(self, *args, **kwargs):
        user = get_current_user()
        user = user if user else None
        if isinstance(user, Profile):
            self.updated_by = user
        super(Profile, self).save(*args, **kwargs)


class EmpData(models.Model):
    emp_name = models.CharField(max_length=255)
    emp_id = models.CharField(max_length=255)
    process = models.CharField(max_length=255)
    dept = models.CharField(max_length=255)
    desi = models.CharField(max_length=255)
    rm1 = models.CharField(max_length=255)
    rm1_id = models.CharField(max_length=255)


# TODO call an api to update miscellaneous changes to update with settings variable.
class Miscellaneous(models.Model):
    # field = models.CharField(choices=MISC_FIELD_CHOICES, max_length=255)
    field = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    updated_by = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return str(self.field)

    def save(self, *args, **kwargs):
        user = get_current_user()

        user = user.emp_id if user and not isinstance(user, AnonymousUser) else None

        misc = Miscellaneous.objects.filter(field=self.field)
        if misc.exists():
            misc.update(content=self.content, updated_by=user)
        else:
            super(Miscellaneous, self).save(*args, **kwargs)


class MiscellaneousMiniFields(models.Model):
    # field = models.CharField(choices=MISC_MINI_FIELDS, max_length=255)
    field = models.CharField(max_length=255, unique=True)
    yes_no = models.BooleanField(default=False)
    content = models.CharField(max_length=255, blank=True, null=True)
    updated_by = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return str(self.field)

    def save(self, *args, **kwargs):
        user = get_current_user()
        # if self.field=="cico_report_last_day" and is:
        user = user.emp_id if user and not isinstance(user, AnonymousUser) else None

        misc = MiscellaneousMiniFields.objects.filter(field=self.field)
        if misc.exists():
            misc.update(content=self.content, updated_by=user)
        else:
            super(MiscellaneousMiniFields, self).save(*args, **kwargs)


class HrmsPermission(models.Model):
    url_name = models.CharField(max_length=150)
    url_route = models.CharField(max_length=255)
    module_name = models.CharField(max_length=150)

    def __str__(self):
        return str(self.module_name) + " - " + str(self.url_name)


class HrmsPermissionGroup(models.Model):
    name = models.CharField(max_length=150)
    category = models.ManyToManyField(Category, blank=True, related_name="category_group_perm")
    permissions = models.ManyToManyField(HrmsPermission, blank=True, related_name="hrms_perms")

    def __str__(self):
        return str(self.name)


class HrmsDeptPermissionGroup(models.Model):
    name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank=True, null=True,
                                   related_name="hrms_dept_perm")
    permissions = models.ManyToManyField(HrmsPermission, blank=True, related_name="hrms_dept_perms")

    def __str__(self):
        return str(self.name)


class EmployeePermissions(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                related_name="profile_emp_perm")
    permissions = models.ManyToManyField(HrmsPermission, blank=True, related_name="emp_permissions")

    def __str__(self):
        return str(self.profile)


class PermissionsToBeRemoved(models.Model):
    permissions = models.ManyToManyField(HrmsPermission, blank=True, related_name="rem_emp_permissions")

    def __str__(self):
        return str(self.id)


class ExceptionLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()


class EmployeeReferral(models.Model):
    referred_by_emp = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="employee_referral_profile")
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="created_by_ref")
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, validators=[validate_email])
    phone_no = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_date = models.DateTimeField(blank=True, null=True)
    referred_emp = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True, related_name="emp_ref_p")
    is_ref_bonus_paid = models.BooleanField(default=False)
    amount = models.IntegerField(default=0)
    is_open = models.BooleanField(default=True)
    status = models.CharField(max_length=30, choices=settings.EMPLOYEE_REFERRAL_STATUS, default="Referred")
    comment = models.CharField(max_length=255, blank=True, null=True)
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name="emp_pro_up", blank=True, null=True)

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and not user.pk:
            user = None
        self.updated_by = user
        super(EmployeeReferral, self).save(*args, **kwargs)


class MappedTeams(models.Model):
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="mapped_created_by")
    from_employee = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name="mapped_from_employee")
    to_employee = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="mapped_to_employee")
    mapped_teams = models.ManyToManyField('team.Team', blank=True, related_name="mapped_teams")
    replaced_employee = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                          related_name="replaced_employee")
    replaced_by = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                    related_name="replaced_by_employee")
    replacement_reason = models.CharField(max_length=255, blank=True, null=True)
    reason = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ReplaceManager(models.Model):
    old_manager = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                    related_name="old_manager")
    new_manager = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="new_manager")
    team = models.ForeignKey("team.Team", on_delete=models.CASCADE, related_name="rep_mgr_team")
    comment = models.CharField(max_length=255)
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                   related_name="cr_by_replace_mgr")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class MappedTeamsHistory(models.Model):
    mapped_teams = models.ForeignKey(MappedTeams, on_delete=models.CASCADE, related_name="mapped_teams_history")
    replaced_employee = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                          related_name="replaced_employee_history")
    replaced_by = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True,
                                    related_name="replaced_by_employee_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class Mapping(models.Model):
    employee = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                 related_name="mapping_employee")
    to_team = models.ForeignKey("team.Team", on_delete=models.SET_NULL, blank=True, null=True,
                                related_name="mapping_to_team")
    from_team = models.ForeignKey("team.Team", on_delete=models.SET_NULL, blank=True, null=True,
                                  related_name="mapping_from_team")
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="mapping_approved_by")
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="mapping_created_by")

    status = models.CharField(max_length=8, choices=settings.MAPPING_STATUS, default="Pending")
    mapped_teams = models.ForeignKey(MappedTeams, on_delete=models.CASCADE, blank=True, null=True,
                                     related_name="mapped_teams_mapping")
    is_open = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.employee)


class Document(models.Model):
    field = models.CharField(max_length=255)
    history_id = models.CharField(max_length=20, blank=True, null=True)
    file = models.FileField(upload_to=document_file, validators=[FileExtensionValidator(
        allowed_extensions=settings.DEFAULT_ALLOWED_EXTENSIONS)])
    file_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_emp_id = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UpdateEmployeeHistory(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="emp_profile")
    field_updated = models.CharField(max_length=1500)
    from_data = models.CharField(max_length=1500, null=True, blank=True)
    to_data = models.CharField(max_length=1500, null=True, blank=True)
    comment = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="profile_updated_by")
    updated_at = models.DateTimeField(auto_now_add=True)
    attachment = models.ManyToManyField(Document, blank=True, related_name="update_employee_attachment")

    def __str__(self):
        return str(self.profile)


class Other(models.Model):
    emp_id = models.CharField(max_length=255, null=True, blank=True)
    char_field = models.CharField(max_length=1500, blank=True, null=True)
    bool_field = models.BooleanField(default=False, blank=True, null=True)
    datetime_field = models.DateTimeField(null=True, blank=True)
    date_field = models.DateField(null=True, blank=True)
    integer_field = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return str(self.emp_id)

class Migration(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField(null=True)

    class Meta:
        db_table = 'django_migrations'  # Link this model to the existing `django_migrations` table
        managed = False  # Prevent Django from trying to manage this table
        verbose_name = 'Migration'
        verbose_name_plural = 'Migrations'
