from django.contrib import admin

from interview_test.models import PreDataQA, TestQA, TestSection, Test, CandidateQASection, CandidateInterviewTest, \
    CandidateInterviewTestTiming, QA
from utils.utils import get_column_names_with_foreign_keys_separate


# Register your models here.

class TestInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Test)
    search_fields = list_display.copy()
    list_display = foreign_keys + list_display


class TestSectionInfo(admin.ModelAdmin):
    list_display = ["id", "test_name", "ts_name", "test", "is_essay"]
    search_fields = ("test__test_name", "id", "ts_name")
    autocomplete_fields = ["test"]

    def test_name(self, obj):
        return obj.test.test_name


class TestQAInfo(admin.ModelAdmin):
    list_display = ["id", "pre_data", "test_name", "ts_name", "test_section", "qa_type", "option_1", "option_2",
                    "option_3", "option_4", "option_5", "max_score", "question", "answer", "text_answer", "created_at",
                    "updated_at"]
    search_fields = ("id", "qa__type", "qa__question", "test_section__test_name")
    autocomplete_fields = ["qa", "pre_data", "test_section"]

    def ts_name(self, obj):
        return obj.test_section.ts_name

    def test_name(self, obj):
        return obj.test_section.test.test_name

    def max_score(self, obj):
        return obj.qa.max_score

    def question(self, obj):
        return obj.qa.question

    def answer(self, obj):
        return obj.qa.answer

    def text_answer(self, obj):
        return obj.qa.text_answer

    def qa_type(self, obj):
        return obj.qa.qa_type

    def option_1(self, obj):
        return obj.qa.option_1

    def option_2(self, obj):
        return obj.qa.option_2

    def option_3(self, obj):
        return obj.qa.option_3

    def option_4(self, obj):
        return obj.qa.option_4

    def option_5(self, obj):
        return obj.qa.option_5


class PreDataQAInfo(admin.ModelAdmin):
    list_display = ["id", "title", "content"]
    search_fields = ("id", "title")


class CandidateQASectionInfo(admin.ModelAdmin):
    list_display = ["id", "candidate", "application", "test_section", "ts_name", "test_name", "section_status",
                    "max_score", "total_score", "total_qns", "total_ans_qns", "created_at", 'updated_at']
    autocomplete_fields = ["candidate", "application", "test_section"]

    def ts_name(self, obj):
        return obj.test_section.ts_name

    def test_name(self, obj):
        return obj.test_section.test.test_name

    search_fields = ("id", "test_section__test__test_name")


class CandidateInterviewTestInfo(admin.ModelAdmin):
    list_display = ["id", "cand_qa_section", "candidate", "application", "qa_type", "test_qa", "is_it_correct",
                    "scored", "answer", "cor_ans", "question", "created_at"]
    search_fields = ("id", "cand_qa_section__id")
    autocomplete_fields = ["cand_qa_section", "test_qa"]

    def qa_type(self, obj):
        return obj.test_qa.qa.qa_type

    def candidate(self, obj):
        return obj.cand_qa_section.candidate

    def application(self, obj):
        return obj.cand_qa_section.application

    def question(self, obj):
        return obj.test_qa.qa.question

    def cor_ans(self, obj):
        return obj.test_qa.qa.answer


class CandidateInterviewTestTimingInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        CandidateInterviewTestTiming)
    search_fields = list_display.copy() + ["candidate__email"]
    list_display = ["test_name"] + foreign_keys + list_display

    def test_name(self, obj):
        return obj.test.test_name


class QAInfo(admin.ModelAdmin):
    list_display = ["id", "qa_type", "option_1", "option_2", "option_3", "option_4", "option_5", "max_score",
                    "question", "answer", "text_answer"]
    search_fields = ("id", "qa_type", "question")


admin.site.register(QA, QAInfo)
admin.site.register(CandidateInterviewTestTiming, CandidateInterviewTestTimingInfo)
admin.site.register(PreDataQA, PreDataQAInfo)
admin.site.register(TestQA, TestQAInfo)
admin.site.register(Test, TestInfo)
admin.site.register(TestSection, TestSectionInfo)
admin.site.register(CandidateQASection, CandidateQASectionInfo)
admin.site.register(CandidateInterviewTest, CandidateInterviewTestInfo)
