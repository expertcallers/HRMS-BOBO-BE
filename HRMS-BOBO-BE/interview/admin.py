from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from interview.models import Candidate, Interviewer, Document, FieldsOfExperience, Application, \
    ToAppliedCandidateStatus, InternPosition, InternQuestion, InternApplication, InternAnswer, CandidateOTPTest
from utils.utils import get_column_names_with_foreign_keys_separate


# Register your models here.

class CandidateInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Candidate)
    search_fields = list_display.copy()
    list_display += foreign_keys


class ApplicationResource(resources.ModelResource):
    class Meta:
        model = Application


class ApplicationInfo(ImportExportModelAdmin):
    search_fields = ('id',)
    autocomplete_fields = ["position_applied", 'to_department', "all_to_departments", "test", "all_interview_persons"]
    list_display = ['id', 'created_at', 'updated_at', 'source', 'source_ref', 'position_applied']
    resource_class = ApplicationResource


class InterviewerResource(resources.ModelResource):
    class Meta:
        model = Interviewer


class InterviewerInfo(ImportExportModelAdmin):
    search_fields = ('id', 'status')
    list_display = [
        'id', 'status', 'interview_emp', 'candidate', 'feedback', 'to_department', 'from_department',
        'total_rounds', 'current_round', "created_at", "updated_at"]
    autocomplete_fields = ['candidate', 'interview_emp', 'interview_files', 'to_department', 'from_department']
    resource_class = InterviewerResource


class InterviewDocumentResource(resources.ModelResource):
    class Meta:
        model = Document


class DocumentInfo(ImportExportModelAdmin):
    search_fields = ("id", "field")
    list_display = ["id", "field", "candidate_id", "file", "filehash"]
    resource_class = InterviewDocumentResource


class FieldsOfExperienceResource(resources.ModelResource):
    class Meta:
        model = FieldsOfExperience


class FieldsOfExperienceInfo(ImportExportModelAdmin):
    search_fields = ('subcategory', 'category')
    list_display = ['category', 'subcategory']
    resource_class = FieldsOfExperienceResource


class ToAppliedCandidateStatusInfo(admin.ModelAdmin):
    search_fields = ("candidate__full_name", "id", "old_application__id", "created_by__emp_id")
    list_display = ["candidate", "old_application", "new_application", "created_by", "created_at", "updated_at"]
    autocomplete_fields = ["candidate", "old_application", "new_application", "created_by"]


class InternApplicationInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(InternApplication)
    search_fields = list_display.copy()
    list_display += foreign_keys


class AnswerResource(resources.ModelResource):
    class Meta:
        model = InternAnswer
        fields = ["intern__name", "intern__phone_no", "question__question_text", "answer_text"]
        export_order = ["intern__name", "intern__phone_no", "question__question_text", "answer_text"]


class AnswerInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(InternAnswer)
    search_fields = list_display.copy()
    list_display = ["question_text"] + list_display + foreign_keys
    resource_class = AnswerResource

    def question_text(self, obj):
        return obj.question.question_text if obj.question else None


class QuestionInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(InternQuestion)
    search_fields = list_display.copy()
    list_display += foreign_keys


class InternPositionInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(InternPosition)
    search_fields = list_display.copy()
    list_display += foreign_keys


class CandidateOTPTestInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(CandidateOTPTest)
    search_fields = list_display.copy()
    list_display += foreign_keys


admin.site.register(CandidateOTPTest, CandidateOTPTestInfo)
admin.site.register(InternApplication, InternApplicationInfo)
admin.site.register(InternAnswer, AnswerInfo)
admin.site.register(InternPosition, InternPositionInfo)
admin.site.register(InternQuestion, QuestionInfo)

admin.site.register(ToAppliedCandidateStatus, ToAppliedCandidateStatusInfo)
admin.site.register(Application, ApplicationInfo)
admin.site.register(FieldsOfExperience, FieldsOfExperienceInfo)
admin.site.register(Candidate, CandidateInfo)
admin.site.register(Interviewer, InterviewerInfo)
admin.site.register(Document, DocumentInfo)
