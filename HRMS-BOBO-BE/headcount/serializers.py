from rest_framework import serializers

from headcount.models import HeadcountProcess, Headcount, ProcessSubCampaign, UpdateProcessRequest, \
    UpdateHeadcountRequest, HeadcountReference


class CreateHeadcountProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeadcountProcess
        exclude = ['sub_campaign']


class SubCampaignSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        return data

    class Meta:
        model = ProcessSubCampaign
        exclude = ['created_by']


class HeadcountProcessSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["sub_campaign"] = SubCampaignSerializer(instance.sub_campaign,
                                                     many=True).data if instance.sub_campaign else None
        data["rm_name"] = instance.rm.full_name if instance.rm else None
        data["rm_emp_id"] = instance.rm.emp_id if instance.rm else None
        edit_request = UpdateProcessRequest.objects.filter(process=instance.id, status="Pending")
        data["is_editable"] = False if edit_request else True
        return data

    class Meta:
        model = HeadcountProcess
        exclude = ['rm', 'sub_campaign']


class HeadcountReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeadcountReference
        fields = '__all__'


class HeadcountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Headcount
        exclude = ['deficit', 'total_hours']


class CreateHeadcountSubCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessSubCampaign
        fields = '__all__'


class CreateUpdateProcessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpdateProcessRequest
        exclude = ['status', 'approved_rejected_by', 'approved_rejected_comment', 'approved_rejected_at']


class UpdateProcessRequestSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        process = instance.process
        data["name"] = process.name
        data["approved_headcount"] = process.approved_headcount
        data["pricing"] = process.pricing
        data["currency"] = process.currency
        data["pricing_type"] = process.pricing_type
        data["pricing_type_value"] = process.pricing_type_value
        data["rm_name"] = process.rm.full_name if process.rm else None
        data["rm_emp_id"] = process.rm.emp_id if process.rm else None
        data[
            "approved_rejected_by_name"] = instance.approved_rejected_by.full_name if instance.approved_rejected_by else None
        data[
            "approved_rejected_by_emp_id"] = instance.approved_rejected_by.emp_id if instance.approved_rejected_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        return data

    class Meta:
        model = UpdateProcessRequest
        exclude = ['process', 'approved_rejected_by', 'created_by']


class ApproveUpdateProcessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpdateProcessRequest
        fields = ['status', 'approved_rejected_by', 'approved_rejected_comment']


class GetHeadcountSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = instance.process.name
        data["approved_headcount"] = instance.process.approved_headcount
        data["sub_campaign"] = instance.sub_campaign.name
        edit_request = UpdateHeadcountRequest.objects.filter(headcount=instance.id, status="Pending")
        data["is_editable"] = False if edit_request else True
        return data

    class Meta:
        model = Headcount
        fields = ['id', 'date', 'scheduled_hc', 'present_hc', 'deficit', 'total_hours', 'created_by', 'created_at']


class GetHeadcountRefSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = instance.process.name
        data["approved_headcount"] = instance.approved_headcount
        scheduled = []
        present = []
        deficit = []
        hours = []
        for hc in instance.headcount.all():
            scheduled.append([hc.sub_campaign.name, round(hc.scheduled_hc, 2)])
            present.append([hc.sub_campaign.name, round(hc.present_hc, 2)])
            deficit.append([hc.sub_campaign.name, round(hc.deficit, 2)])
            hours.append(hc.total_hours)
        data["scheduled_hc"] = scheduled
        data["present_hc"] = present
        data["deficit"] = deficit
        data["total_hours"] = round(sum(hours), 2)
        data["target_revenue"] = round(instance.target_revenue, 2)
        data["achieved_revenue"] = round(instance.achieved_revenue, 2)
        data["leakage_revenue"] = round(instance.leakage_revenue, 2)
        edit_request = UpdateHeadcountRequest.objects.filter(headcount__in=instance.headcount.all(), status="Pending")
        data["is_editable"] = False if edit_request else True
        return data

    class Meta:
        model = HeadcountReference
        exclude = ("headcount", "process")


class UpdateHeadcountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpdateHeadcountRequest
        fields = ['headcount', 'old_scheduled_hc', 'scheduled_hc', 'old_present_hc', 'present_hc', 'comment',
                  'created_by']


class ApproveUpdateHeadcountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpdateHeadcountRequest
        fields = ['status', 'approved_rejected_by', 'approved_rejected_comment']


class GetUpdateHeadcountSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data[
            "approved_rejected_by_name"] = instance.approved_rejected_by.full_name if instance.approved_rejected_by else None
        data[
            "approved_rejected_by_emp_id"] = instance.approved_rejected_by.emp_id if instance.approved_rejected_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        headcount_proc = HeadcountProcess.objects.filter(sub_campaign=instance.headcount.sub_campaign).last()
        data["process"] = headcount_proc.name if headcount_proc else None
        data["sub_campaign"] = instance.headcount.sub_campaign.name if instance.headcount else None
        return data

    class Meta:
        model = UpdateHeadcountRequest
        exclude = ['created_by', 'approved_rejected_by']


class HeadcountReferenceIndivSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sub_campaign"] = instance.sub_campaign.name
        headcount_ref = HeadcountReference.objects.filter(headcount=instance.id).last()
        data["approved_headcount"] = headcount_ref.approved_headcount if headcount_ref else None
        return data

    class Meta:
        model = Headcount
        exclude = ['deficit', 'total_hours', 'created_by']
