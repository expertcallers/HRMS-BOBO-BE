import json
import logging
import traceback
from datetime import datetime
from django.db.models import Q, Count
from rest_framework.response import Response
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from hrms import settings
from mapping.models import Profile, Designation, Department, MappedTeams, ReplaceManager
from mapping.serializer import GetAllProfileSerializer, GetProfileSerializer, GetMyTeamSerializer
from mapping.views import HasUrlPermission
from team.models import Team, Process
from team.serializer import CreateTeamSerializer, GetTeamSerializer, GetEmpUnderTeamSerializer, \
    AppendNameEmpIDSerializer, HierarchySerializer, MappingTeamSerializer, ERFInterviewerSerializer, \
    GetAllTeamsSerializer, GetAllProcessSerializer, GetAllDesignationSerializer, GetAllDepartmentSerializer, \
    GetAllMappedTeamsSerializer, GetAllReplaceTeamManagerSerializer
from utils.util_classes import CustomTokenAuthentication
from utils.utils import return_error_response, update_request, get_team_ids, get_sort_and_filter_by_cols, \
    get_iexact_for_list, update_my_team, get_connected_managers_list, get_emp_by_emp_id, get_my_team, get_all_managers, \
    get_team_by_id, get_all_managers_include_emp, update_qms_profiles, get_my_team_process, check_server_status, \
    get_all_profile_serializer_map_columns
import logging

# Create your views here.

logger = logging.getLogger(__name__)


class GetMyTeam(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllProfileSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            usr = request.user
            my_team = get_team_ids(usr)
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=get_all_profile_serializer_map_columns)
            if my_team:
                my_team.append(usr.team.id)
            else:
                my_team = [usr.team.id]
            self.queryset = Profile.objects.filter(is_active=True, team__in=my_team).select_related(
                'team__manager').prefetch_related(
                'onboard__candidate__current_application').filter(search_query).filter(
                **filter_by).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetMyTeam {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetTeamsUnderManager(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetMyTeamSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            usr = request.user
            my_team = get_team_ids(usr)
            map_fields = {"base_team": "team__base_team__name", "team": "team__name"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_fields)
            if my_team is None:
                self.queryset = []
            else:
                self.queryset = Profile.objects.filter(is_active=True, team__in=my_team).filter(search_query).filter(
                    **filter_by).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetMyTeam {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetAllEmp(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllProfileSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=get_all_profile_serializer_map_columns)
        self.queryset = Profile.objects.filter(is_superuser=0).select_related('team__manager').prefetch_related(
            'onboard__candidate__current_application').filter(search_query).filter(**filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetAllInactiveEmp(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllProfileSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=get_all_profile_serializer_map_columns)
        self.queryset = Profile.objects.filter(is_active=False,
                                               last_working_day__lt=datetime.today().date()).select_related(
            'team__manager').prefetch_related(
            'onboard__candidate__current_application').filter(
            search_query).filter(**filter_by).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_emp(request):
    try:
        usr = request.user
        profile = GetProfileSerializer(usr).data
        return HttpResponse(json.dumps(profile))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_teams_list_under_manager(request, emp_id):
    try:
        profile = Profile.objects.filter(emp_id=emp_id).last()
        if profile is None:
            return HttpResponse(json.dumps({"teams": {}}))
        my_team = get_my_team_process(profile)
        return HttpResponse(json.dumps({"teams": my_team}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_base_team(request):
    try:
        serializer = CreateTeamSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)

        team = Process.objects.create(name=serializer.validated_data['name'])
        return HttpResponse(json.dumps({"id": team.id, "name": team.name}))

    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_team(request):
    try:
        usr = request.user
        manager = request.data.get("manager")
        if manager is None or manager == "":
            raise ValueError("please select valid manager from the list")
        try:
            pro = Profile.objects.get(emp_id=manager, is_active=True)
        except Exception as e:
            raise ValueError("Manager not found for given emp-id {0}".format(manager))
        data = update_request(request.data, manager=pro.id)
        serializer = CreateTeamSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        try:
            _ = Process.objects.get(id=serializer.validated_data['base_team'].id, is_active=True)
        except Exception as e:
            logger.info("{0}".format(str(e)))
            raise ValueError("invalid base-team information")
        serializer.validated_data["created_by"] = usr
        team = serializer.create(serializer.validated_data)
        pro.my_team.add(team)
        pro.save()
        update_my_team(get_all_managers(pro))
        team = GetTeamSerializer(team).data
        return HttpResponse(json.dumps(team))

    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_tl_am_mgr(request):
    try:
        designation = request.data.get("designation")
        if designation is None or designation == "":
            raise ValueError("Please provide the valid designation")
        name = request.data.get('name', "")
        process_id = request.data.get("process_id")

        if designation == "manager":
            q = get_iexact_for_list("designation__category__name", settings.MANAGER_AND_ABOVE)
        elif designation == "am_mgr":
            q = get_iexact_for_list("designation__category__name", ["AM"] + settings.MANAGER_AND_ABOVE)
        elif designation == "it_employee":
            profiles = Profile.objects.filter(team__base_team__department__name="IT")
        else:
            q = get_iexact_for_list("designation__category__name", ["TL", "AM"] + settings.MANAGER_AND_ABOVE)

        if designation != "it_employee":
            profiles = Profile.objects.filter(q).filter(is_active=True)

        if process_id:
            process = Process.objects.filter(id=process_id, is_active=True).last()
            if process:
                profiles = profiles.filter(team__base_team__department=process.department)

        if not name:
            profiles = profiles.order_by("id")
        else:
            profiles = profiles.filter(
                Q(emp_id=name) | Q(first_name__icontains=name) | Q(middle_name__icontains=name) | Q(
                    last_name__icontains=name) | Q(full_name__icontains=name)).order_by("id")
        return HttpResponse(json.dumps({"result": ERFInterviewerSerializer(profiles, many=True).data}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_team_name(request):
    try:
        field = request.data.get("field")
        team_name = request.data.get("team_name")
        base_team = request.data.get('base_team')
        if field not in ["name"]:
            return Response({"result": []})

        if base_team is None or base_team == []:
            return Response({"result": []})
        try:
            base_ids = Process.objects.filter(id__in=base_team, is_active=True).values_list('id', flat=True)
        except Exception as e:
            raise ValueError("invalid base-team information is provided")
        if field == "name":
            if team_name:
                teams = list(
                    Team.objects.filter(name__icontains=team_name, base_team__id__in=base_ids, is_active=True))
            else:
                teams = list(Team.objects.filter(base_team__id__in=base_ids, is_active=True))
            return HttpResponse(json.dumps({"result": MappingTeamSerializer(teams, many=True).data}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_base_team(request):
    try:
        name = request.data.get("name")
        if name:
            teams = list(
                Process.objects.filter(name__icontains=name, is_active=True).values_list("id", "name", named=True))
        else:
            teams = list(Process.objects.filter(is_active=True).values_list("id", "name", named=True))
        return HttpResponse(json.dumps({"result": teams}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_base_team_by_department(request):
    try:
        department = request.data.get("departments", [])
        if department:
            if "all" in department:
                process_names = list(Process.objects.filter(is_active=True).values_list('id', 'name', named=True))
            else:
                process_names = list(
                    Process.objects.filter(department__in=department, is_active=True).values_list('id', 'name',
                                                                                                  named=True))
        else:
            process_names = []
        return HttpResponse(json.dumps({"result": process_names}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_team_info(team):
    profiles = Profile.objects.filter(team=team, is_active=True)
    team_info = HierarchySerializer(profiles, many=True)
    return team_info.data


def get_bottom_up_team_info(profile, team_info):
    if profile.team.manager == profile:
        team_info.append(HierarchySerializer(profile).data)
        return team_info
    profile = profile.team.manager
    team_info.append(HierarchySerializer(profile).data)
    return get_bottom_up_team_info(profile, team_info)


def get_top_down_team_info(profile, team_info):
    my_team = profile.my_team.all()
    for team in my_team:
        team_info += get_team_info(team)
    return team_info


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_team_hierarchy(request):
    try:
        profile = request.user
        hierarchy = []
        if not profile.team.manager == profile:
            hierarchy += get_team_info(profile.team)
        if not profile.my_team.all().count() == 0:
            hierarchy += get_top_down_team_info(profile, [])
        hierarchy += (get_bottom_up_team_info(profile, []))
        return HttpResponse(json.dumps(hierarchy[::-1]))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_active_emp_ids(request):
    try:
        name = request.data.get("name")
        profiles = []
        if name:
            profiles = Profile.objects.filter(is_active=True, status__iexact="Active").filter(
                Q(emp_id__icontains=name) | Q(first_name__icontains=name) | Q(middle_name__icontains=name) | Q(
                    last_name__icontains=name)).order_by("id")
            profiles = AppendNameEmpIDSerializer(profiles, many=True).data
        return HttpResponse(json.dumps({"result": profiles}))
    except Exception as e:
        logger.info("exception at get_all_emp_ids {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_emp_ids(request):
    try:
        name = request.data.get("name")
        profiles = []
        if name:
            profiles = Profile.objects.filter(
                Q(emp_id__icontains=name) | Q(first_name__icontains=name) | Q(middle_name__icontains=name) | Q(
                    last_name__icontains=name)).order_by("id")
            profiles = AppendNameEmpIDSerializer(profiles, many=True).data
        return HttpResponse(json.dumps({"result": profiles}))
    except Exception as e:
        logger.info("exception at get_all_emp_ids {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_emp_under_team(request):
    try:
        team = request.data.get('team')
        if team is None:
            raise ValueError("Please provide the team information")
        team = team.split(",")
        name = request.data.get("name")
        if name:
            profiles = Profile.objects.filter(is_active=True, team__in=team, status__iexact="Active").filter(
                Q(emp_id__icontains=name) | Q(first_name__icontains=name) | Q(middle_name__icontains=name) | Q(
                    last_name__icontains=name))
        else:
            profiles = Profile.objects.filter(is_active=True, team__in=team, status__iexact="Active")
        res = GetEmpUnderTeamSerializer(profiles, many=True).data
        return HttpResponse(json.dumps({"result": res}))
    except Exception as e:
        logger.info("exception at get_emp_under_team {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllTeam(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllTeamsSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):

        map_columns = {"manager_emp_id": "manager__emp_id", "manager_name": "manager__full_name",
                       "manager_2_emp_id": "manager__team__manager__emp_id",
                       "manager_2_name": "manager__team__manager__full_name",
                       "manager_3_emp_id": "manager__team__manager__emp_id",
                       "manager_3_name": "manager__team__manager__full_name",
                       "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                       "process": "base_team__name", "department": "base_team__department__name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        try:
            self.queryset = Team.objects.filter(is_active=True).filter(search_query).filter(**filter_by).annotate(
                employee_count=Count("team")).order_by(
                *order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllTeam {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetMyTeamList(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllTeamsSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user

        map_columns = {"manager_emp_id": "manager__emp_id", "manager_name": "manager__full_name",
                       "manager_2_emp_id": "manager__team__manager__emp_id",
                       "manager_2_name": "manager__team__manager__full_name",
                       "manager_3_emp_id": "manager__team__manager__emp_id",
                       "manager_3_name": "manager__team__manager__full_name",
                       "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                       "process": "base_team__name", "department": "base_team__department__name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        try:
            my_team = get_team_ids(usr)
            if my_team is None:
                my_team = []
            self.queryset = Team.objects.filter(is_active=True, id__in=my_team).filter(search_query).filter(
                **filter_by).annotate(employee_count=Count("team")).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetMyTeamList {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetAllProcess(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllProcessSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                       "department": "department__name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        try:
            self.queryset = Process.objects.filter(is_active=True).filter(search_query).filter(**filter_by).order_by(
                *order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllProcess {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetAllDesignation(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllDesignationSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"category": "category__name", "department": "department__name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        try:
            self.queryset = Designation.objects.exclude(name="other").filter(search_query).filter(**filter_by).order_by(
                *order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllDesignation {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetAllDepartment(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllDepartmentSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        try:
            self.queryset = Department.objects.exclude(name="other").filter(search_query).filter(**filter_by).order_by(
                *order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllDepartment {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetAllMappedTeams(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllMappedTeamsSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"from_employee_emp_id": "from_employee__emp_id",
                       "from_employee_name": "from_employee__full_name",
                       "to_employee_emp_id": "to_employee__emp_id", "to_employee_name": "to_employee__full_name",
                       "replaced_employee_emp_id": "replaced_employee__emp_id",
                       "replaced_employee_name": "replaced_employee__full_name",
                       "replaced_by_emp_id": "replaced_by__emp_id", "replaced_by_name": "replaced_by__full_name"
                       }
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        try:
            self.queryset = MappedTeams.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllDepartment {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


class GetAllReplaceTeamManager(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllReplaceTeamManagerSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"new_manager_emp_id": "new_manager__emp_id", "new_manager_name": "new_manager__full_name",
                       "old_manager_emp_id": "old_manager__emp_id", "old_manager_name": "old_manager__full_name",
                       "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                       "team": "team__name", "process": "team__base_team__name",
                       "department": "team__base_team__department__name"
                       }
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        try:
            self.queryset = ReplaceManager.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("exception at GetAllDepartment {0}".format(traceback.format_exc(5)))
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def replace_mapped_teams(request, mapped_teams_id):
    try:
        if not str(mapped_teams_id).isdecimal():
            raise ValueError("invalid mapped teams id")
        usr = request.user
        replacement_reason = request.data.get("replacement_reason")
        if replacement_reason is None or str(replacement_reason).strip() == "":
            raise ValueError("please provide the replacement reason")
        mapped_teams = MappedTeams.objects.filter(id=mapped_teams_id).last()
        if mapped_teams is None:
            raise ValueError("please provide the valid mapped-teams-id")
        new_replacement_emp = request.data.get("new_replaced_employee")
        replaced_employee = get_emp_by_emp_id(new_replacement_emp)
        for team in mapped_teams.mapped_teams.all():
            team.manager = replaced_employee
            team.updated_by = usr
            team.save()
        mapped_teams.replaced_employee = replaced_employee
        mapped_teams.replaced_by = usr
        mapped_teams.replacement_reason = replacement_reason
        mapped_teams.save()
        update_my_team()
        update_qms_profiles()
        return HttpResponse(json.dumps({"message": "Mapped teams replaced successfully"}))
    except Exception as e:
        logger.info("exception at replace_mapped_teams {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_custom_my_team(request):
    try:
        my_team = get_my_team(request.user)
        return HttpResponse(json.dumps({"my_team": my_team}))
    except Exception as e:
        logger.info("exception at get_custom_my_team {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_team_manager(request):
    try:
        usr = request.user
        new_manager = request.data.get("new_mgr_emp_id")
        if new_manager is None or str(new_manager) == "":
            raise ValueError("Please provide the valid new manager emp-id")
        new_mgr = get_emp_by_emp_id(new_manager)
        team = get_team_by_id(request.data.get('team'))
        if team.manager == new_mgr:
            raise ValueError("both new manager and old manager are same for the team")
        comment = request.data.get("comment")
        if comment is None or str(comment).strip() == "":
            raise ValueError("Please provide the valid comment")

        rep_mgr = ReplaceManager.objects.create(new_manager=new_mgr, old_manager=team.manager, created_by=usr,
                                                team=team, comment=comment)
        team.manager = new_mgr
        team.save()
        update_my_team()
        update_qms_profiles()
        return HttpResponse(json.dumps(
            {"message": "Successfully updated the new manager {0} to team {1}".format(new_mgr.emp_id, team.name)}))
    except Exception as e:
        logger.info("exception at update_team_manager {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_my_team_api(request):
    try:
        update_my_team()
        if settings.ENABLE_QMS_INTEGRATION and check_server_status(settings.QMS_URL):
            update_qms_profiles()
        return HttpResponse(json.dumps({"message": "Successfully updated my teams"}))
    except Exception as e:
        logger.info("exception at update_my_team_api {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
