from django.core.exceptions import ValidationError
from rest_framework import serializers

from mapping.models import Profile, Designation, Department, MappedTeams, ReplaceManager
from team.models import Team, Process
from utils.utils import get_formatted_name, get_custom_emp_response
from hrms import settings


class CreateBaseTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = ["name"]

    def validate_name(self, value):
        # Perform a case-insensitive check for uniqueness
        if Process.objects.filter(name__iexact=value).exists():
            raise ValidationError("The name must be unique (case-insensitive).")
        return value


class CreateTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["name", "base_team", "manager"]

    def validate_name(self, value):
        base_team = self.initial_data.get("base_team")
        # Perform a case-insensitive check for uniqueness
        if Team.objects.filter(name__iexact=value, base_team_id=base_team).exists():
            raise ValidationError("The team-name must be unique (case-insensitive) for the selected base-team.")
        return value


class GetTeamSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["manager"] = instance.manager.emp_id
        data["manager_name"] = instance.manager.full_name
        return data

    class Meta:
        model = Team
        fields = ["name", "manager"]


class GetEmpUnderTeamSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        return get_custom_emp_response(instance)

    class Meta:
        model = Profile
        fields = ["emp_id", "first_name", "middle_name", "last_name"]


class AppendNameEmpIDSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        return get_custom_emp_response(instance)

    class Meta:
        model = Profile
        fields = ["full_name", "emp_id"]


class HierarchySerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["base_team"] = instance.team.base_team.name if instance.team else None
        data["my_team"] = ";".join(
            Team.objects.filter(manager=instance).exclude(id=instance.team.id).values_list('name', flat=True))
        data["team"] = instance.team.name if instance.team else None
        data["designation"] = instance.designation.name if instance.designation else None
        data["name"] = instance.full_name
        data["image"] = settings.MEDIA_URL + str(instance.image) if instance.image else None
        data["manager_emp_id"] = instance.team.manager.emp_id if instance.team.manager else None
        data["team_id"] = instance.team.id
        return data

    class Meta:
        model = Profile
        fields = ["emp_id"]


class MappingTeamSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        team_name = str(instance.name) + " - " + str(get_formatted_name(instance.manager)) + " (" + str(
            instance.manager.emp_id) + ")"
        return [instance.id, team_name]

    class Meta:
        model = Team
        fields = ["id", "name", "manager"]


class ERFInterviewerSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        return get_custom_emp_response(instance)

    class Meta:
        model = Profile
        fields = ["id", "first_name", "middle_name", "last_name"]


class GetAllTeamsSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        created_by = instance.created_by
        process = instance.base_team
        manager = instance.manager
        data["manager_emp_id"] = manager.emp_id if manager else None
        data["manager_name"] = manager.full_name if manager else None
        data["manager_2_emp_id"] = manager.team.manager.emp_id if manager else None
        data["manager_2_name"] = manager.team.manager.full_name if manager else None
        data["manager_3_emp_id"] = manager.team.manager.team.manager.emp_id if manager else None
        data["manager_3_name"] = manager.team.manager.team.manager.full_name if manager else None
        data["created_by_emp_id"] = created_by.emp_id if created_by else None
        data["created_by_name"] = created_by.full_name if created_by else None
        data["process"] = process.name if process else None
        data["department"] = process.department.name if process else None
        data["employee_count"] = instance.employee_count
        return data

    class Meta:
        model = Team
        fields = "__all__"


class GetAllProcessSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        created_by = instance.created_by
        data["created_by_emp_id"] = created_by.emp_id if created_by else None
        data["created_by_name"] = created_by.full_name if created_by else None
        data["department"] = instance.department.name if instance.department else None
        return data

    class Meta:
        model = Process
        fields = "__all__"


class GetAllDesignationSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["department"] = instance.department.name if instance.department else None
        data["category"] = instance.category.name if instance.category else None
        return data

    class Meta:
        model = Designation
        fields = "__all__"


class GetAllDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class GetAllMappedTeamsSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["from_employee_emp_id"] = instance.from_employee.emp_id if instance.from_employee else None
        data["from_employee_name"] = instance.from_employee.full_name if instance.from_employee else None
        data["to_employee_emp_id"] = instance.to_employee.emp_id if instance.to_employee else None
        data["to_employee_name"] = instance.to_employee.full_name if instance.to_employee else None
        data["mapped_teams"] = "; ".join(i.name for i in instance.mapped_teams.all())
        data["replaced_employee_emp_id"] = instance.replaced_employee.emp_id if instance.replaced_employee else None
        data["replaced_employee_name"] = instance.replaced_employee.full_name if instance.replaced_employee else None
        data["replaced_by_emp_id"] = instance.replaced_by.emp_id if instance.replaced_by else None
        data["replaced_by_name"] = instance.replaced_by.full_name if instance.replaced_by else None
        return data

    class Meta:
        model = MappedTeams
        fields = "__all__"


class GetAllReplaceTeamManagerSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["new_manager_emp_id"] = instance.new_manager.emp_id if instance.new_manager else None
        data["new_manager_name"] = instance.new_manager.full_name if instance.new_manager else None
        data["old_manager_emp_id"] = instance.old_manager.emp_id if instance.old_manager else None
        data["old_manager_name"] = instance.old_manager.full_name if instance.old_manager else None
        data["team"] = instance.team.name if instance.team else None
        data["process"] = instance.team.base_team.name if instance.team and instance.team.base_team else None
        data["department"] = instance.team.base_team.department.name if data[
                                                                            "process"] and instance.team.base_team.department else None
        return data

    class Meta:
        model = ReplaceManager
        exclude = ["created_by", "new_manager", "old_manager", "team"]
