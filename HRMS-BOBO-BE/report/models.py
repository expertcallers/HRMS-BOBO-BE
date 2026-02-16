from django.apps import apps
from django.db import models

from team.models import Process


# Create your models here.
class ReportFile(models.Model):
    process = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    sheet_name = models.CharField(max_length=255, blank=True, null=True)
    upload_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.CharField(max_length=50, blank=True, null=True)
    uploaded_by_name = models.CharField(max_length=255, blank=True, null=True)
    month = models.IntegerField(null=True)
    year = models.IntegerField(null=True)

    def __str__(self):
        return str(self.id)


class SLATaskReference(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return str(self.id)


class SLA(models.Model):
    task = models.ForeignKey(SLATaskReference, on_delete=models.SET_NULL, blank=True, null=True,
                             related_name="sla_task")
    index = models.CharField(max_length=255)
    metric = models.CharField(max_length=255)
    metric_id = models.IntegerField(blank=True, null=True)
    date = models.DateField()
    value = models.CharField(max_length=50)
    report_file = models.ForeignKey(ReportFile, related_name="bigo_sla_report_file", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class TA(models.Model):
    main_task = models.CharField(max_length=255)
    main_task_id = models.IntegerField(blank=True, null=True)
    task = models.ForeignKey(SLATaskReference, on_delete=models.SET_NULL, blank=True, null=True,
                             related_name="ta_task")
    index_for_the_whole_team = models.CharField(max_length=255, null=True)
    weight = models.CharField(max_length=6, null=True)
    daily_target_of_the_whole_team = models.CharField(max_length=255, null=True)
    days = models.IntegerField(null=True, blank=True)
    days_achieved_the_target = models.FloatField(null=True, blank=True)
    achieved_ratio = models.CharField(max_length=6, null=True)
    date = models.DateField(blank=True, null=True)
    month = models.IntegerField(null=True)
    year = models.IntegerField(null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="bigo_ta_report_file", on_delete=models.CASCADE,
                                    null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class GbmDialer(models.Model):
    date = models.DateField(blank=True, null=True)
    emp_id = models.CharField(max_length=20, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    ph_no = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    no_of_attempt = models.CharField(max_length=255, blank=True, null=True)
    call_status_dispo = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    call_type = models.CharField(max_length=255, blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="gbm_dialer_report_file", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class GbmLead(models.Model):
    emp_id = models.CharField(max_length=20, blank=True, null=True)
    agent_name = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    leads_mined = models.IntegerField(blank=True, null=True)
    leads_created = models.IntegerField(blank=True, null=True)
    prospect_created = models.IntegerField(blank=True, null=True)
    nomination_received = models.IntegerField(blank=True, null=True)
    doc_collected = models.IntegerField(blank=True, null=True)
    shortlisted = models.IntegerField(blank=True, null=True)
    negotiation = models.IntegerField(blank=True, null=True)
    invoice = models.IntegerField(blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="gbm_lead_report_file", on_delete=models.CASCADE,
                                    null=True, blank=True)
    sales = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class GbmEmail(models.Model):
    emp_id = models.CharField(max_length=20, blank=True, null=True)
    agent_name = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    unique_email = models.IntegerField(blank=True, null=True)
    follow_up = models.IntegerField(blank=True, null=True)
    agent_replies = models.IntegerField(blank=True, null=True)
    client_response_received = models.IntegerField(blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="gbm_email_report_file", on_delete=models.CASCADE,
                                    null=True, blank=True)

    total_emails = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class GbmCall(models.Model):
    emp_id = models.CharField(max_length=20, blank=True, null=True)
    agent_name = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    connected_calls = models.IntegerField(blank=True, null=True)
    non_connect = models.IntegerField(blank=True, null=True)
    total_dialled_count = models.IntegerField(blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="gbm_call_report_file", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class AadyaSolutions(models.Model):
    date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    connect_type = models.CharField(max_length=255, blank=True, null=True)
    user = models.CharField(max_length=255, blank=True, null=True)
    call_type = models.CharField(choices=[("b2b", "b2b"), ("b2c", "b2c")], max_length=3, blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="aadhya_solutions", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class Insalvage(models.Model):
    date = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=16, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    aluminum_siding = models.FloatField(blank=True, null=True)
    aluminum_sheet = models.FloatField(blank=True, null=True)
    copper_sheet = models.FloatField(blank=True, null=True)
    steel = models.FloatField(blank=True, null=True)
    status = models.CharField(max_length=30, blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="insalvage", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class Medicare(models.Model):
    date = models.DateField(blank=True, null=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    number = models.CharField(max_length=16, blank=True, null=True)
    appt_date = models.DateField(blank=True, null=True)
    appt_time = models.CharField(max_length=8, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="medicare_report", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class SapphireMedical(models.Model):
    timestamp = models.DateTimeField(blank=True, null=True)
    patient_name = models.CharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gp_name = models.CharField(max_length=350, blank=True, null=True)
    phone_1 = models.CharField(max_length=16, blank=True, null=True)
    phone_2 = models.CharField(max_length=16, blank=True, null=True)
    email = models.EmailField()
    call_duration_as_per_zendesk = models.CharField(max_length=8, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    dispositions = models.CharField(max_length=350, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    ticket_no = models.IntegerField(blank=True, null=True)
    agent_names = models.CharField(max_length=255, blank=True, null=True)
    calling_sheet = models.CharField(max_length=255, blank=True, null=True)
    flagged_lead = models.CharField(max_length=255, blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="sapphire_report", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class Capgemini(models.Model):
    call_date = models.DateField(blank=True, null=True)
    company_name = models.CharField(max_length=350, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=15, blank=True, null=True)
    disposition = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    called_by = models.CharField(max_length=255, blank=True, null=True)
    current_system_name = models.CharField(max_length=255, blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="capgemini_report", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class BBM(models.Model):
    emp_id = models.IntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    center = models.CharField(max_length=255, blank=True, null=True)
    agent_name = models.CharField(max_length=255, blank=True, null=True)
    disposition = models.CharField(max_length=255, blank=True, null=True)
    call_type = models.CharField(max_length=255, blank=True, null=True)
    report_file = models.ForeignKey(ReportFile, related_name="bbm_report", on_delete=models.CASCADE,
                                    null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)
