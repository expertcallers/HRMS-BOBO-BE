from django.db import models
from mapping.models import Profile, Department
from hrms import settings


class Resignation(models.Model):
    resignation_message = models.TextField()
    resignation_status = models.CharField(max_length=10, choices=settings.RESIGNATION_STATUS)
    applied_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='applied_by')
    start_date = models.DateField()
    exit_date = models.DateField()
    notice_period_in_days = models.IntegerField(default=30)
    accepted_or_rejected_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                                related_name='accepted_or_rejected_by')
    accepted_or_rejected_comment = models.CharField(max_length=255, null=True, blank=True)
    accepted_or_rejected_at = models.DateTimeField(null=True, blank=True)
    hr_accepted_or_rejected_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                                related_name='hr_accepted_or_rejected_by')
    hr_accepted_or_rejected_comment = models.CharField(max_length=255, null=True, blank=True)
    hr_accepted_or_rejected_at = models.DateTimeField(null=True, blank=True)
    notice_period_extended_or_reduced_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                                             related_name='notice_period_extended_or_reduced_by')
    notice_period_extended_or_reduced_comments = models.CharField(max_length=255, null=True, blank=True)
    notice_period_extended_or_reduced_at = models.DateTimeField(null=True, blank=True)
    is_notice_period_reduced = models.BooleanField(default=False)
    it_team_approval = models.BooleanField(default=False)
    it_team_comments = models.CharField(max_length=500, null=True, blank=True)
    hr_team_approval = models.BooleanField(default=False)
    hr_team_comments = models.CharField(max_length=500, null=True, blank=True)
    admin_team_approval = models.BooleanField(default=False)
    admin_team_comments = models.CharField(max_length=500, null=True, blank=True)
    dept_approval = models.BooleanField(default=False)
    dept_approval_comments = models.CharField(max_length=500, null=True, blank=True)
    withdrawal_comments = models.CharField(max_length=255, null=True, blank=True)
    knowledge_transfer = models.BooleanField(default=False)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ResignationHistory(models.Model):
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE, related_name='resignation_history')
    transaction = models.CharField(max_length=55)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class ExitFeedbackInterview(models.Model):
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE, related_name='resignation_feedback')
    primary_reason = models.CharField(max_length=500)
    job_satisfaction_level = models.CharField(max_length=20, choices=settings.SATISFACTION_LEVEL)
    work_env_rating = models.CharField(max_length=10, choices=settings.EXIT_FEEDBACK_RATING)
    mgr_relation_rating = models.CharField(max_length=10, choices=settings.EXIT_FEEDBACK_RATING)
    team_relation_rating = models.CharField(max_length=10, choices=settings.EXIT_FEEDBACK_RATING)
    training_rating = models.CharField(max_length=20, choices=settings.TRAINING_FEEDBACK_RATING)
    hr_process_rating = models.CharField(max_length=10, choices=settings.EXIT_FEEDBACK_RATING)
    suggestions = models.TextField()
    open_comment = models.TextField()
    future_intention = models.TextField(null=True, blank=True)
    additional_info = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class ExitChecklist(models.Model):
    content = models.TextField()
    dept = models.ForeignKey(Department, on_delete=models.SET_NULL, related_name='exit_checklist_dept', null=True,
                             blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class FinalApprovalChecklist(models.Model):
    checklist = models.ForeignKey(ExitChecklist, on_delete=models.CASCADE, related_name='approval_checklist')
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE, related_name='approval_resignation')
    due_status = models.CharField(max_length=3, choices=settings.EXIT_FORM_CHOICES)
    approved_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='approved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)
