import logging
from datetime import datetime

import pytz
from rest_framework import serializers

from hrms import settings
from interview_test.models import TestQA, CandidateInterviewTestTiming, CandidateInterviewTest, QA, Test, PreDataQA, \
    TestSection
from utils.utils import hash_value, calculate_remaining_duration

tz = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger(__name__)


class GetTestQuestionsByTestSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        qa = GetAllQASerializer(instance.qa).data
        for key, value in qa.items():
            if key in ["id", "answer", "text_answer"]:
                continue
            data[key] = value
        return data

    class Meta:
        model = TestQA
        fields = "__all__"


class GetTestNameSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        # offset = instance.created_at.utcoffset()
        # date = instance.created_at
        # logger.info("date={0} offset ={1}".format(date, offset))
        # date = date + offset
        # date_str = f"{date.year}{date.month}{date.day}{date.hour}{date.minute}{date.second}"
        # logger.info("date_str{0} date{1}".format(date, date_str))

        emp_id = instance.created_by.emp_id if instance.created_by else None
        if emp_id:
            return [instance.id, str(instance.test_name) + "-" + str(instance.created_by)]
        return [instance.id, str(instance.test_name)]

    class Meta:
        model = Test
        fields = "__all__"


class GetInterviewTestTimingSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["remaining_duration"] = calculate_remaining_duration(instance.actual_test_end_time)
        data["candidate"] = hash_value(instance.candidate.id, 'cd')
        data["name"] = instance.candidate.full_name
        data["email"] = instance.candidate.email
        data["test_name"] = instance.test.test_name
        data["test_duration"] = instance.test.duration
        data["pass_percent"] = instance.test.pass_percent
        return data

    class Meta:
        model = CandidateInterviewTestTiming
        exclude = ("candidate",)


class GetAllQASerializer(serializers.ModelSerializer):
    class Meta:
        model = QA
        fields = "__all__"


class GetAllTestQASerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        qa_data = GetAllQASerializer(instance.qa).data
        for key, value in qa_data.items():
            if key in ["id"]:
                continue
            data[key] = value
        data["test"] = instance.test_section.test.id
        data["duration"] = instance.test_section.test.duration
        data["ts_name"] = instance.test_section.ts_name
        data["test_name"] = instance.test_section.test.test_name
        data["pre_data_title"] = instance.pre_data.title if instance.pre_data else None
        data["pre_data_content"] = instance.pre_data.content if instance.pre_data else None
        data["created_by_name"] = instance.qa.created_by.full_name if instance.qa.created_by else None
        data["created_by_emp_id"] = instance.qa.created_by.emp_id if instance.qa.created_by else None
        data["updated_by_name"] = instance.qa.updated_by.full_name if instance.qa.updated_by else None
        data["updated_by_emp_id"] = instance.qa.updated_by.emp_id if instance.qa.updated_by else None
        return data

    class Meta:
        model = TestQA
        fields = "__all__"


class GetAllCandidateInterviewTestQASerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["application"] = instance.cand_qa_section.application.id
        data["test_qa"] = GetAllTestQASerializer(instance.test_qa).data if instance.test_qa else None
        return data

    class Meta:
        model = CandidateInterviewTest
        fields = "__all__"


class UpdateQASerializer(serializers.ModelSerializer):
    class Meta:
        model = QA
        fields = "__all__"


class UpdatePreDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreDataQA
        fields = "__all__"


class UpdateTestSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSection
        fields = "__all__"


class UpdateTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ["test_name", "duration", "updated_by"]


class GetAllPreDataSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["updated_by_name"] = instance.updated_by.full_name if instance.updated_by else None
        data["updated_by_emp_id"] = instance.updated_by.emp_id if instance.updated_by else None
        return data

    class Meta:
        model = PreDataQA
        fields = "__all__"


class GetAllTestSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSection
        fields = "__all__"


class GetAllTestSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["updated_by_name"] = instance.updated_by.full_name if instance.updated_by else None
        data["updated_by_emp_id"] = instance.updated_by.emp_id if instance.updated_by else None
        return data

    class Meta:
        model = Test
        fields = "__all__"
