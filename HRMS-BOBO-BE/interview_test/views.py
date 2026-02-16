import re
from datetime import datetime, timedelta
import json
import logging
import traceback

import pytz
from django.db.models import Sum, Q
from django.shortcuts import render
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from django.http.response import HttpResponse

from hrms import settings
from interview.models import Candidate
from interview.views import get_candidate_info_by_id
from interview_test.models import Test, TestSection, PreDataQA, TestQA, CandidateQASection, CandidateInterviewTest, \
    CandidateInterviewTestTiming, QA
from interview_test.serializers import GetTestQuestionsByTestSerializer, GetInterviewTestTimingSerializer, \
    GetAllCandidateInterviewTestQASerializer, GetAllTestQASerializer, GetTestNameSerializer, UpdateQASerializer, \
    GetAllPreDataSerializer, GetAllTestSectionSerializer, GetAllTestSerializer, UpdatePreDataSerializer, \
    UpdateTestSectionSerializer, UpdateTestSerializer
from mapping.views import HasUrlPermission
from utils.util_classes import CustomTokenAuthentication
from utils.utils import validate_files, read_test_question_file_format_output, get_sort_and_filter_by_cols, \
    format_text_answer, unhash_value, get_candidate_interview_timing, check_if_candidate_rejected, \
    calculate_remaining_duration, create_candidate_test_section, evaluate_essay_by_chat_gpt_in_json_format, \
    return_error_response, update_request

logger = logging.getLogger(__name__)
tz = pytz.timezone(settings.TIME_ZONE)


# Create your views here.
def get_and_validate_test_status(cd_id, candidate=None):
    if candidate is None:
        candidate = get_candidate_info_by_id(cd_id)
    check_if_candidate_rejected(candidate)
    cur_app = candidate.current_application
    erf = cur_app.position_applied
    if erf is None:
        raise ValueError(
            "Candidate has not been assigned with any ERF, candidate not chosen proper erf from position-applied during application, please contact admin")
    test = cur_app.test
    if test is None:
        raise ValueError("There is no associated test for the candidate application, please contact admin")
    cd_test_timing = get_candidate_interview_timing(candidate, cur_app, test)
    return cd_test_timing, candidate, cur_app, erf, test


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_tests_list(reqeust):
    try:
        # tests = Test.objects.all()
        # test_data = GetTestNameSerializer(tests, many=True).data
        tests = list(Test.objects.all().values_list("id", "test_name"))
        return HttpResponse(json.dumps({"tests": tests}))
    except Exception as e:
        logger.info("exception at get_all_tests_list {0} ".format(str(e)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


# TODO setup sockets if time to complete need to synchronized properly
@api_view(["GET"])
def get_test_info(request, test_id):
    try:
        test = Test.objects.filter(id=test_id).last()
        if test is None:
            raise ValueError("Invalid test-id")
        return HttpResponse(json.dumps({"test_name": test.test_name, "total_duration": test.duration}))
    except Exception as e:
        logger.info("exception at get_test_info {0} ".format(str(e)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def validate_test_headings(xl_data, heading_list):
    for key in heading_list:
        data = xl_data.get(key)
        if data is None or str(data).strip() == "":
            raise ValueError("Please provide the value for {0}".format(key))


def validate_test_qa(qa_model_list, pre_data, xl_data, qa_list, test_section, usr):
    for key in qa_list:
        data = xl_data.get(key)
        if data is None or len(data) == 0 or len(data) > 0 and data[0] == "":
            raise ValueError("Please provide for the proper value for {0}".format(key))
    option_1 = xl_data["option_1"]
    option_2 = xl_data["option_2"]
    option_3 = xl_data["option_3"]
    option_4 = xl_data.get("option_4")
    option_5 = xl_data.get("option_5")
    q_type = xl_data["qa_type"]
    answer = xl_data["answer"]
    max_score = xl_data["max_score"]
    question = xl_data.get("question")
    if len(q_type) != len(option_2) or len(q_type) != len(option_3) or (
            question and len(q_type) != len(q_type)) or len(q_type) != len(answer) or len(q_type) != len(
        option_1) or len(max_score) != len(q_type):
        raise ValueError("mismatch with number of options, questions and answer and max_score")
    count = 0
    existing_qa = []
    for op_1 in option_1:
        if op_1 is None:
            break
        score = max_score[count]
        qn = question[count] if question else None
        op_2 = option_2[count]
        op_3 = option_3[count]
        op_4 = option_4[count] if option_4 else None
        op_5 = option_5[count] if option_5 else None
        ans = answer[count]
        q_typ = str(q_type[count]).lower() if q_type[count] else None
        if not score or not str(score).isdecimal():
            raise ValueError("Please provide valid max_score")
        if q_typ is None or str(q_typ).strip() == "" or q_typ not in ["single", "multiple", "text"]:
            raise ValueError(
                "qa_type should have single or multiple or text value, reference option_1={0}".format(op_1))
        if ans is None or str(ans).strip() == "":
            raise ValueError("answer should have value, reference option_1={0}".format(op_1))
        if q_typ in ["single", "multiple"] and (qn is None or str(qn).strip() == ""):
            raise ValueError("question should have value, reference option_1={0}".format(op_1))

        if not op_1 or not op_2 and not op_3:
            raise ValueError("No proper options for question {0}".format(qn))
        if op_5 and not op_4:
            raise ValueError("There is no option_4 but option_5 exists for question {0}".format(qn))

        if q_typ == "multiple":
            ans = ",".join(str(i).strip().lower() for i in str(ans).split(","))
        elif q_typ == "text":
            ans = format_text_answer(ans)

        if q_typ in ["single", "multiple"]:
            qa = QA.objects.filter(option_1=op_1, option_2=op_2, option_3=op_3, option_4=op_4, option_5=op_5,
                                   qa_type=q_typ, question=qn, max_score=score).last()
        else:
            qa = QA.objects.filter(option_1=op_1, option_2=op_2, option_3=op_3, option_4=op_4, option_5=op_5,
                                   qa_type=q_typ, question=qn, max_score=score).last()
        if qa:
            existing_qa.append(qa)
        else:
            if q_typ in ["single", "multiple"]:
                qa_model_list.append(
                    QA(option_1=op_1, option_2=op_2, option_3=op_3, option_4=op_4, option_5=op_5, qa_type=q_typ,
                       answer=ans, question=qn, max_score=score, created_by=usr))
            elif q_typ == "text":
                qa_model_list.append(
                    QA(option_1=op_1, option_2=op_2, option_3=op_3, option_4=op_4, option_5=op_5, qa_type=q_typ,
                       text_answer=ans, question=qn, max_score=score, created_by=usr))
        count += 1
    return qa_model_list, existing_qa


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication, HasUrlPermission])
@permission_classes([IsAuthenticated])
def upload_test_questions(request):
    try:
        usr = request.user
        # TODO Check for maximum size and number of files that can be uploaded at once
        mcq_files = request.FILES.getlist("mcq")
        duration = request.data.get("duration")
        is_essay = json.loads(request.data.get("has_essay", "false"))
        if duration is None or str(duration) == "" or not str(duration).isdecimal():
            raise ValueError("Invalid test duration input, must be in minutes")
        if mcq_files and len(mcq_files) > 0:
            validate_files(request.FILES, "interview_test")
        create_uploaded_files = []
        for xl_file in mcq_files:
            qa_model_list = []
            xl_data = read_test_question_file_format_output(xl_file)
            # logger.info("xl_data ={0}".format(xl_data))
            validate_test_headings(xl_data, ["test_name", "test_section", "pass_percent"])
            pre_data_title = xl_data.get("pre_data_title")
            pre_data_content = xl_data.get("pre_data_content")
            pass_percent = xl_data.get("pass_percent")
            if pass_percent is None or not str(pass_percent).isdigit():
                raise ValueError("Please provide pass_percent from 0-100")

            pre_data_content = str(pre_data_content).strip() if pre_data_content and pre_data_content != "" else None
            pre_data_title = str(pre_data_title).strip() if pre_data_title and pre_data_title != "" else None
            pre_data = None
            if pre_data_title:
                pre_data, created = PreDataQA.objects.get_or_create(title__iexact=pre_data_title,
                                                                    content__iexact=pre_data_content,
                                                                    defaults={"title": pre_data_title,
                                                                              "created_by": usr,
                                                                              "content": pre_data_content})

            test, created = Test.objects.get_or_create(test_name__iexact=xl_data["test_name"],
                                                       defaults={"test_name": xl_data["test_name"],
                                                                 "created_by": usr,
                                                                 "pass_percent": pass_percent,
                                                                 "duration": duration, "has_essay": is_essay})
            if not created:
                test.duration = duration
                test.pass_percent = pass_percent
                test.save()
            if is_essay:
                essay_name = "Essay for " + str(test.test_name)
                test_section, created = TestSection.objects.get_or_create(
                    test=test, ts_name__iexact=essay_name,
                    defaults={"test": test, "ts_name": essay_name, "is_essay": True, "created_by": usr})
                qa, created = QA.objects.get_or_create(qa_type="essay",
                                                       defaults={"qa_type": "essay", "max_score": 0, "created_by": usr})
                test_qa, created = TestQA.objects.get_or_create(test_section=test_section, qa=qa,
                                                                defaults={"qa": qa, "test_section": test_section,
                                                                          "pre_data": None, "created_by": usr})

            test_section, created = TestSection.objects.get_or_create(
                test=test, ts_name__iexact=xl_data["test_section"], defaults={
                    "test": test, "ts_name": xl_data["test_section"], "created_by": usr})

            # tests = Test.objects.filter(test_name__istartswith=xl_data["test_name"]).count()
            #
            # test_name = str(xl_data["test_name"]) + " " + str(tests)
            # test = Test.objects.create(test_name=test_name, duration=duration, has_essay=is_essay)
            # if is_essay:
            #     essay_name = "Essay for " + str(test.test_name)
            #     test_section = TestSection.objects.create(test=test, ts_name=essay_name, is_essay=True)
            #     qa, created = QA.objects.get_or_create(qa_type="essay", max_score=0,
            #                                            defaults={"qa_type": "essay", "max_score": 0})
            #     test_qa = TestQA.objects.create(test_section=test_section, qa=qa, pre_data=None)
            #
            # test_section = TestSection.objects.create(test=test, ts_name=xl_data["test_section"])

            qa_model_list, existing_qa = validate_test_qa(qa_model_list, pre_data, xl_data,
                                                          ["option_1", "option_2", "option_3", "answer", "qa_type",
                                                           "max_score"],
                                                          test_section, usr)

            if len(qa_model_list) > 0 or len(existing_qa) > 0:
                create_uploaded_files.append(
                    {"qa_model_list": qa_model_list, "existing_qa": existing_qa, "test_section": test_section,
                     "pre_data": pre_data})
            else:
                logger.info("no changes made with file {0}".format(xl_file.name))
        for qa_cmb in create_uploaded_files:
            test_qa_query_list = QA.objects.bulk_create(qa_cmb.get("qa_model_list"))
            test_qa_list = []
            test_section = qa_cmb.get("test_section")
            pre_data = qa_cmb.get("pre_data")
            for i in test_qa_query_list:
                test_qa_list.append(
                    TestQA(qa=i, test_section=test_section, pre_data=pre_data))
            existing_qa = qa_cmb.get("existing_qa")
            for i in existing_qa:
                test_qa = TestQA.objects.filter(qa=i, test_section=test_section, pre_data=pre_data).last()
                if test_qa is None:
                    test_qa_list.append(
                        TestQA(qa=i, test_section=test_section, pre_data=pre_data))
            TestQA.objects.bulk_create(test_qa_list)

        return HttpResponse(json.dumps({"message": "Files processed successfully "}))



    except Exception as e:
        logger.info("exception at upload_mcq_questions {0} ".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def form_question_obj(test_qa):
    return {"question": test_qa.qa.question, "option_1": test_qa.qa.option_1, "option_2": test_qa.qa.option_2,
            "option_3": test_qa.qa.option_3, "option_4": test_qa.qa.option_4, "option_5": test_qa.qa.option_5,
            'qa_type': test_qa.qa.qa_type, "id": test_qa.id}


def set_completion_status_for_qa_section(cand_qa_section):
    section_qns_count = TestQA.objects.filter(test_section=cand_qa_section.test_section).count()
    cand_int_test_ans_qns = CandidateInterviewTest.objects.filter(cand_qa_section=cand_qa_section)
    cand_int_test_ans_qns_count = cand_int_test_ans_qns.count()
    if cand_int_test_ans_qns_count == 0:
        cand_qa_section.total_score = 0
    else:
        cand_qa_section.total_score = cand_int_test_ans_qns.aggregate(total=Sum('scored'))["total"]
    cand_qa_section.total_ans_qns = cand_int_test_ans_qns_count

    if section_qns_count == cand_int_test_ans_qns_count:
        cand_qa_section.section_status = "Completed"
    cand_qa_section.save()

    if cand_int_test_ans_qns_count > section_qns_count:
        raise ValueError("Please contact admin, the number of answered records are more than actual questions")


def aggregate_score(candidate, application, test):
    cand_qa_sec_list = CandidateQASection.objects.filter(
        candidate=candidate, application=application, erf=application.erf)
    for cand_qa_section in cand_qa_sec_list:
        cand_int_test = CandidateInterviewTest.objects.filter(cand_qa_section=cand_qa_section).values_list("score")


def set_cd_qa_completion_status(candidate, application, test, cd_int_tm):
    cand_qa_sec_list = CandidateQASection.objects.filter(
        candidate=candidate, application=application, erf=application.position_applied)
    pending_count = cand_qa_sec_list.filter(section_status__in=["Current", "Pending"]).count()
    remaining_duration = calculate_remaining_duration(cd_int_tm.actual_test_end_time)
    if pending_count == 0 or (remaining_duration == 0 and cd_int_tm.test_status == "Started"):
        calculate_and_update_test_complesion_stats(cd_int_tm, cand_qa_sec_list, datetime.now().replace(microsecond=0))
        logger.info("candidate {0} with application {1} marked completed status for assessment {0} ".format(
            candidate, application, test.test_name))


def get_cur_section_and_pending_section(candidate, cur_app, test_id):
    candidate_attd_sections = CandidateQASection.objects.filter(
        candidate=candidate, erf=cur_app.position_applied, section_status__in=["Pending", "Current"],
        application=cur_app)
    current_section = candidate_attd_sections.filter(section_status="Current").last()
    pending_sections = candidate_attd_sections.filter(section_status="Pending")
    return current_section, pending_sections


def get_cur_section_question_mark_pending_if_any(candidate, cur_app, test, cd_test_timing):
    try:
        candidate_attd_sections = CandidateQASection.objects.filter(
            candidate=candidate, erf=cur_app.position_applied, section_status__in=["Pending", "Current"],
            application=cur_app)

        current_section = candidate_attd_sections.filter(section_status="Current").last()
        pending_sections = candidate_attd_sections.filter(section_status="Pending")

        if current_section is None:
            if pending_sections.count() == 0:
                set_cd_qa_completion_status(candidate, cur_app, test, cd_test_timing)
                return [], None, None, None, True
            else:
                current_section = pending_sections[0]
                current_section.section_status = "Current"
                current_section.save()
        test_section = current_section.test_section
        cnd_int_test_list = CandidateInterviewTest.objects.filter(cand_qa_section=current_section)

        answered_test_q = list(cnd_int_test_list.values_list("test_qa__id", flat=True))

        test_questions = TestQA.objects.filter(test_section=current_section.test_section).exclude(
            id__in=answered_test_q)
        no_pre_data_qns = test_questions.filter(pre_data__isnull=True)

        formatted_no_pre_data_qns = {"questions": [form_question_obj(p_data) for p_data in no_pre_data_qns],
                                     "pre_data_title": None, "pre_data_content": None}
        pre_data_qns = test_questions.filter(pre_data__isnull=False)
        pre_data_response_qns = {}
        for data in pre_data_qns:
            p_id = data.pre_data.id
            if p_id in pre_data_response_qns.keys():
                pre_data_response_qns[p_id]["questions"].append(form_question_obj(data))
            else:
                pre_data_response_qns[p_id] = {"questions": [form_question_obj(data)],
                                               "pre_data_title": data.pre_data.title,
                                               "pre_data_content": data.pre_data.content
                                               }

        all_questions_response = list(pre_data_response_qns.values())
        if no_pre_data_qns.count() != 0:
            all_questions_response = list(pre_data_response_qns.values()) + [formatted_no_pre_data_qns]
        if len(all_questions_response) == 0:
            set_completion_status_for_qa_section(current_section)
            return get_cur_section_question_mark_pending_if_any(candidate, cur_app, test, cd_test_timing)
        set_cd_qa_completion_status(candidate, cur_app, test, cd_test_timing)
        return all_questions_response, current_section, test_section, test, False
    except RecursionError as e:
        # TODO add a mail to developer, project_manager, to fix the critical error
        logger.info("RecursionError something went wrong")
        return [], None, None, None, False


@api_view(["GET"])
def get_test_questions_by_test_name(request, cd_id):
    try:
        cd_test_timing, candidate, cur_app, erf, test = get_and_validate_test_status(cd_id)
        if cd_test_timing is None:
            raise ValueError(
                "There is no interview-test-timing associated for this candidate application, please contact admin")
        completed_test_dict = {"message": "Candidate has completed assessment of {0}".format(
            cur_app.test.test_name), "completed": True}

        if cd_test_timing.test_status != "Started":
            return HttpResponse(json.dumps(completed_test_dict))

        all_questions_response, current_section, test_section, test, test_completed = get_cur_section_question_mark_pending_if_any(
            candidate, cur_app, test, cd_test_timing)

        if cd_test_timing.test_status != "Started":
            return HttpResponse(json.dumps(completed_test_dict))

        return HttpResponse(json.dumps(
            {"qa_data": all_questions_response, "test_name": test.test_name if test else None,
             "completed": test_completed,
             "test_section": test_section.ts_name if test_section else None,
             "cand_qa_section": current_section.id if current_section else None,
             "message": "continue for next section"}))

    except Exception as e:
        logger.info("exception at get_test_questions_by_test_name {0} ".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def validate_answers(answer_list):
    cand_int_test_list = []
    cand_qa_sec_list_dict = {}
    for ans_data in answer_list:
        test_qa_id = ans_data.get("test_qa_id")
        ans = ans_data.get("answer")
        cand_qa_section = ans_data.get("cand_qa_section")

        test_qa = TestQA.objects.filter(id=test_qa_id).last()
        if test_qa is None:
            raise ValueError("invalid test id")

        if ans is None or ans == "":
            ans = None
        if cand_qa_section is None or cand_qa_section == "" or not str(cand_qa_section).isdecimal():
            raise ValueError("Invalid candidate-qa-section value")
        if cand_qa_section not in cand_qa_sec_list_dict.keys():
            cand_qa_sec_list_dict[cand_qa_section] = CandidateQASection.objects.filter(id=cand_qa_section).last()
            if cand_qa_sec_list_dict[cand_qa_section] is None:
                raise ValueError("Invalid Candidate QA Section ID")

        existing_answer_count = CandidateInterviewTest.objects.filter(
            cand_qa_section=cand_qa_sec_list_dict[cand_qa_section], test_qa=test_qa).count()
        if existing_answer_count > 0:
            continue

        qa_type = str(test_qa.qa.qa_type).lower()
        is_it_correct = False
        cor_text_answer = format_text_answer(test_qa.qa.text_answer)
        cor_answer = str(test_qa.qa.answer).strip()
        answer = None
        text_answer = None
        essay_answer = None
        essay_feedback = None
        scored = 0
        if qa_type == "single":
            answer = ans
            if ans == cor_answer:
                is_it_correct = True
        elif qa_type == "multiple":
            ans = [str(i).strip().lower() for i in ans.split(",")]
            answer = ",".join(i for i in ans)
            cor_ans = cor_answer.split(",")
            if len(ans) == len(cor_ans):
                is_it_correct = True
                for i in cor_ans:
                    i = str(i).strip().lower()
                    if i not in ans:
                        is_it_correct = False
                        break
        elif qa_type == "text":
            text_answer = format_text_answer(ans)
            # logger.info("text_answer = {0}".format(text_answer))
            # logger.info("text_cor_answer ={0}".format(cor_text_answer))
            if cor_text_answer == text_answer:
                is_it_correct = True
                # logger.info("text_came inside True")
        elif qa_type == "essay":
            essay_answer = ans
            chatgpt_j_response = evaluate_essay_by_chat_gpt_in_json_format(ans)
            # logger.info("chatgpt_j_response {0}".format(chatgpt_j_response))
            essay_feedback = chatgpt_j_response.get("feedback", "contact-admin no feedback from cgpt")
            # essay_feedback = None
            is_it_correct = True
            if ans is None or str(ans).strip() == "":
                is_it_correct = False

        if is_it_correct and qa_type != "essay":
            scored = test_qa.qa.max_score
        cand_int_test_list.append(CandidateInterviewTest(
            is_it_correct=is_it_correct, cand_qa_section=cand_qa_sec_list_dict[cand_qa_section], test_qa=test_qa,
            answer=answer, text_answer=text_answer, scored=scored, essay_answer=essay_answer,
            essay_feedback=essay_feedback))
    return cand_int_test_list, cand_qa_sec_list_dict


@api_view(["POST"])
def submit_test_answer(request):
    try:
        ans_data = request.data.get("ans_data")
        if ans_data is None or ans_data == "" or type(ans_data) != list:
            raise ValueError("No answer received, invalid input format")
        cand_int_test_list, cand_qa_sec_list_dict = validate_answers(ans_data)
        cd_qa_sec = None
        cd_int_tm = None
        if len(cand_qa_sec_list_dict.keys()) > 0:
            cd_qa_sec = list(cand_qa_sec_list_dict.values())[0]
            cd_int_tm = get_candidate_interview_timing(cd_qa_sec.candidate, cd_qa_sec.application,
                                                       cd_qa_sec.test_section.test)
            if cd_int_tm is None:
                raise ValueError("There is no candidate-interview-test-timing record, contact admin")

        if len(cand_int_test_list) > 0:
            CandidateInterviewTest.objects.bulk_create(cand_int_test_list)
        for cand_qa_section in list(cand_qa_sec_list_dict.values()):
            set_completion_status_for_qa_section(cand_qa_section)
        if cd_qa_sec and cd_int_tm:
            set_cd_qa_completion_status(cd_qa_sec.candidate, cd_qa_sec.application, cd_qa_sec.test_section.test,
                                        cd_int_tm)
        return HttpResponse(json.dumps({}))
    except Exception as e:
        logger.info("exception at submit_test_answer {0} ".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetTestQuestionsByTestSection(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetTestQuestionsByTestSerializer
    model = serializer_class.Meta.model

    def get(self, request, ts_id, *args, **kwargs):
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET)

        self.queryset = TestQA.objects.filter(test_section__id=ts_id).filter(**filter_by).filter(search_query).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_test(request):
    try:
        pass
        # test_name = request.data.get("test_name")
        # duration = request.data.get("duration")
        # if test_name is None or test_name == "":
        #     raise ValueError("Please provide the test name")
        # test = Test.objects.create(test_name=test_name,duration=du)
    except Exception as e:
        logger.info("exception at create_test {0} ".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}))


# TODO use CandidateInterviewTestTiming to check the status of test
def calculate_and_update_test_complesion_stats(cd_test_timing, cand_qa_sec_list, current_time, test_status="Completed"):
    cand_stats = cand_qa_sec_list.aggregate(total_score=Sum("total_score"), total_ans_qns=Sum("total_ans_qns"),
                                            total_qns=Sum("total_qns"),
                                            max_score=Sum("max_score"))
    cd_test_timing.cnd_test_end_time = current_time
    cd_test_timing.test_status = test_status
    cd_test_timing.max_score = cand_stats.get("max_score")
    cd_test_timing.total_questions = cand_stats.get("total_qns")
    cd_test_timing.total_ans_questions = cand_stats.get("total_ans_qns")
    cd_test_timing.total_score = cand_stats.get("total_score")
    percentage = (cd_test_timing.total_score / cd_test_timing.max_score) * 100
    if cd_test_timing.test.pass_percent:
        if int(percentage) >= cd_test_timing.test.pass_percent:
            cd_test_timing.result = "Pass"
        else:
            cd_test_timing.result = "Fail"
    cd_test_timing.percentage = percentage
    cd_test_timing.save()


def get_candidate_qa_sec_list(candidate, application, test):
    return CandidateQASection.objects.filter(
        candidate=candidate, application=application, erf=application.position_applied)


@api_view(["GET"])
def start_end_status_test(request, cd_id):
    try:
        cd_test_timing, candidate, cur_app, erf, test = get_and_validate_test_status(cd_id)
        current_time = datetime.now().replace(microsecond=0)
        end_time = current_time + timedelta(minutes=test.duration)

        created = False
        if cd_test_timing is None:
            total_qns_count = TestQA.objects.filter(test_section__test=test).count()
            cand_qa_sec_list = get_candidate_qa_sec_list(candidate, cur_app, test)
            create_candidate_test_section(cand_qa_sec_list, candidate, cur_app, test)
            if total_qns_count == 0:
                raise ValueError(
                    "There are no questions in the test {0}, questions need to be uploaded, please contact admin".format(
                        test.test_name))

            cd_test_timing = CandidateInterviewTestTiming.objects.create(
                candidate=candidate, application=cur_app, erf=cur_app.position_applied, test_status="Started",
                cnd_test_start_time=current_time, actual_test_end_time=end_time, total_questions=total_qns_count,
                test=test
            )

            created = True

        if not created:
            is_time_exceeded = tz.localize(current_time) >= (cd_test_timing.actual_test_end_time + timedelta(minutes=1))
            if is_time_exceeded and cd_test_timing.test_status == "Started":
                cand_qa_sec_list = get_candidate_qa_sec_list(candidate, cur_app, test)
                calculate_and_update_test_complesion_stats(cd_test_timing, cand_qa_sec_list, current_time,
                                                           test_status="Force Completed")
                logger.info("candidate {0} with application {1} marked Force Completed for assessment {0} ".format(
                    candidate, cur_app, test.test_name))

        cd_test_timing = GetInterviewTestTimingSerializer(cd_test_timing).data
        return HttpResponse(json.dumps(cd_test_timing))

    except Exception as e:
        logger.info("exception at start_test {0} ".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllInterviewTestTiming(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetInterviewTestTimingSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"name": "candidate__full_name", "email": "candidate__email", "test_name": "test__test_name",
                          "test_duration": "test__duration", "erf": "erf__id"}
        try:
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_look_up)
            self.queryset = CandidateInterviewTestTiming.objects.filter(**filter_by).filter(search_query).order_by(
                *order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllInterviewTestTiming {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetCandidateInterviewTestTiming(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetInterviewTestTimingSerializer
    model = serializer_class.Meta.model

    def get(self, request, candidate_id, *args, **kwargs):
        candidate = unhash_value(candidate_id, 'cd')
        fields_look_up = {"name": "candidate__full_name", "email": "candidate__email", "test_name": "test__test_name",
                          "test_duration": "test__duration", "erf": "application__position_applied__id",
                          "created_by_name": "created_by__name",
                          "created_by_emp_id": "created_by__emp_id",
                          "updated_by_emp_id": "updated_by__emp_id",
                          "updated_by_name": "updated_by__name",
                          }
        try:
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_look_up)
            self.queryset = CandidateInterviewTestTiming.objects.filter(candidate=candidate).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllInterviewTestTiming {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetAllCandidateInterviewTest(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllCandidateInterviewTestQASerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            fields_look_up = {"qa_type": "test_qa__qa__qa_type", "ts_name": "cand_qa_section__test_section__ts_name",
                              "test_name": "cand_qa_section__test_section__test__test_name",
                              "test_id": "cand_qa_section__test_section__test__id",
                              "answer": "test_qa__qa__answer", "question": "test_qa__qa__question",
                              "option_1": "test_qa__qa__option_1", "option_2": "test_qa__qa__option_2",
                              "option_3": "test_qa__qa__option_3", "option_4": "test_qa__qa__option_4",
                              "option_5": "test_qa__qa__option_5", "max_score": "test_qa__qa__max_score",
                              "text_answer": "test_qa__qa__text_answer",
                              "erf": "cand_qa_section__erf__id",
                              "application": "cand_qa_section__application__id"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_look_up)
            self.queryset = CandidateInterviewTest.objects.filter(**filter_by).filter(search_query).order_by(
                *order_by_cols)
        except Exception as e:
            logger.info("exception at GetAllCandidateInterviewTest {0}".format(traceback.format_exc(5)))
            self.queryset = []
        return self.list(request, *args, **kwargs)


class GetAllTestQA(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllTestQASerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            fields_look_up = {"ts_name": "test_section__ts_name", "test_name": "test_section__test__test_name",
                              "pre_data_title": "pre_data__title", "pre_data_content": "pre_data__content",
                              "answer": "qa__answer", "question": "qa__question",
                              "option_1": "qa__option_1", "option_2": "qa__option_2",
                              "option_3": "qa__option_3", "option_4": "qa__option_4",
                              "option_5": "qa__option_5", "max_score": "qa__max_score", "qa_type": "qa__qa_type",
                              "text_answer": "qa__text_answer",
                              "created_by_name": "qa__created_by__full_name",
                              "created_by_emp_id": "qa__created_by__emp_id",
                              "updated_by_emp_id": "qa__updated_by__emp_id",
                              "updated_by_name": "qa__updated_by__full_name",
                              }
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_look_up)
            self.queryset = TestQA.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        except Exception as e:
            logger.info("exception at GetAllTestQA {0}".format(traceback.format_exc(5)))
            self.queryset = []
        return self.list(request, *args, **kwargs)


class GetAllTest(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllTestSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            map_fields = {"created_by_name": "created_by__full_name", "created_by_emp_id": "created_by__emp_id",
                          "updated_by_name": "created_by__full_name", "updated_by_emp_id": "updated_by__emp_id"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_fields)
            self.queryset = Test.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        except Exception as e:
            logger.info("exception at GetAllTest {0}".format(traceback.format_exc(5)))
            self.queryset = []
        return self.list(request, *args, **kwargs)


class GetAllTestSection(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllTestSectionSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET)
            self.queryset = TestSection.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        except Exception as e:
            logger.info("exception at GetAllTestSection {0}".format(traceback.format_exc(5)))
            self.queryset = []
        return self.list(request, *args, **kwargs)


class GetAllPreData(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllPreDataSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET)
            self.queryset = PreDataQA.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        except Exception as e:
            logger.info("exception at GetAllPreData {0}".format(traceback.format_exc(5)))
            self.queryset = []
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_qa(request, qa_id):
    try:
        usr = request.user
        qa = QA.objects.filter(id=qa_id).last()
        if qa is None:
            raise ValueError("invalid qa-id is provided")
        data = update_request(request.data, updated_by=usr.id)
        serializer = UpdateQASerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.update(qa, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "qa updated successfully"}))
    except Exception as e:
        logger.info("exception at update_qa {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_pre_data(request, pre_data_id):
    try:
        usr = request.user

        pre_data = PreDataQA.objects.filter(id=pre_data_id).last()
        if pre_data is None:
            raise ValueError("invalid qa-id is provided")
        data = update_request(request.data, updated_by=usr.id)

        serializer = UpdatePreDataSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.update(pre_data, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "pre-data updated successfully"}))
    except Exception as e:
        logger.info("exception at update_pre_data {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_test_section(request, test_section_id):
    try:
        usr = request.user
        test_section = TestSection.objects.filter(id=test_section_id).last()
        if test_section is None:
            raise ValueError("invalid test-section-id is provided")
        data = update_request(request.data, updated_by=usr.id)
        serializer = UpdateTestSectionSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.update(test_section, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "test-section updated successfully"}))
    except Exception as e:
        logger.info("exception at update_test_section {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_test(request, test_id):
    try:
        usr = request.user

        test = Test.objects.filter(id=test_id).last()
        if test is None:
            raise ValueError("invalid test-id is provided")
        data = update_request(request.data, updated_by=usr.id)

        serializer = UpdateTestSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.update(test, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "test updated successfully"}))
    except Exception as e:
        logger.info("exception at update_test {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
