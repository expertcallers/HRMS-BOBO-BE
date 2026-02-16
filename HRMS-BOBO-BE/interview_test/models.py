from django.db import models

from hrms import settings
from interview.models import Candidate, Application
from mapping.models import Profile


# Create your models here.
class PreDataQA(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="pre_data_created_by")
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="pre_data_updated_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class Test(models.Model):
    test_name = models.CharField(max_length=255)
    duration = models.IntegerField(default=40)
    pass_percent = models.IntegerField()
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="test_created_by")
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="test_updated_by")
    has_essay = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class TestSection(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="test_sec_sub")
    ts_name = models.CharField(max_length=255)
    is_essay = models.BooleanField(default=False)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="test_section_created_by")
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="test_section_updated_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class QA(models.Model):
    qa_type = models.CharField(max_length=8, choices=settings.QUESTION_TYPE)
    option_1 = models.CharField(max_length=300, blank=True, null=True)
    option_2 = models.CharField(max_length=300, blank=True, null=True)
    option_3 = models.CharField(max_length=300, blank=True, null=True)
    option_4 = models.CharField(max_length=300, blank=True, null=True)
    option_5 = models.CharField(max_length=300, blank=True, null=True)
    question = models.CharField(max_length=500, blank=True, null=True)
    answer = models.CharField(max_length=10, blank=True, null=True)
    max_score = models.IntegerField(default=1)
    text_answer = models.CharField(max_length=900, blank=True, null=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="qa_created_by")
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="qa_updated_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class TestQA(models.Model):
    pre_data = models.ForeignKey(PreDataQA, blank=True, null=True, on_delete=models.SET_NULL,
                                 related_name="mcq_pre_data")
    test_section = models.ForeignKey(TestSection, on_delete=models.CASCADE, related_name="test_section_name")
    qa = models.ForeignKey(QA, on_delete=models.CASCADE, related_name="test_qa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


# based on the pagination
# based on the reached_pagination = True send the next_test_section_qtn


# check has_mcq has_textq and send the questions accordingly

class CandidateQASection(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="inter_candidate")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="inter_applcn")
    erf = models.ForeignKey("erf.ERF", on_delete=models.CASCADE, related_name="cnd_qa_sec_erf")
    test_section = models.ForeignKey(TestSection, on_delete=models.CASCADE, related_name="inter_test_sec")
    section_status = models.CharField(max_length=10,
                                      choices=[("Completed", "Completed"), ("Pending", "Pending"),
                                               ("Current", "Current")], default="Pending")
    total_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=0)
    total_ans_qns = models.IntegerField(default=0)
    total_qns = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class CandidateInterviewTest(models.Model):
    cand_qa_section = models.ForeignKey(CandidateQASection, on_delete=models.CASCADE, related_name="cand_inter_test_qa")
    test_qa = models.ForeignKey(TestQA, on_delete=models.CASCADE, null=True, related_name="inter_test_q")
    answer = models.CharField(max_length=20, null=True)
    text_answer = models.CharField(max_length=900, null=True)
    essay_answer = models.TextField(blank=True, null=True)
    essay_feedback = models.CharField(max_length=255, blank=True, null=True)
    is_it_correct = models.BooleanField(default=False)
    scored = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class CandidateInterviewTestTiming(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="inter_timing_candidate")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="inter_timing_applcn")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="test_timing_sec_sub")
    erf = models.ForeignKey('erf.ERF', on_delete=models.CASCADE, related_name="test_erf")
    cnd_test_start_time = models.DateTimeField()
    cnd_test_end_time = models.DateTimeField(blank=True, null=True)
    test_status = models.CharField(max_length=15, choices=settings.INTERVIEW_TEST_STATUS)
    actual_test_end_time = models.DateTimeField()
    total_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=0)
    percentage = models.IntegerField(blank=True, null=True)
    result = models.CharField(max_length=4, choices=settings.TEST_RESULT, blank=True, null=True)
    total_questions = models.IntegerField(default=0)
    total_ans_questions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)
