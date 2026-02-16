from rest_framework import serializers
from tax.models import IT, IT80C, OtherChapVIADeductions, HouseRentAllowance, HouseRentInfo, MedicalSec80D, \
    HouseProperty, HousePropertyIncomeLoss, OtherIncome


class CreateITSerializer(serializers.ModelSerializer):
    class Meta:
        model = IT
        fields = ["profile", "from_year", "to_year"]


class CreateIT80CSerializer(serializers.ModelSerializer):
    class Meta:
        model = IT80C
        exclude = ("total_declared", "created_at", "updated_at", "it")


class CreateOtherChapVIADeductionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherChapVIADeductions
        exclude = ("total_declared", "created_at", "updated_at", "it")


class IT80CSerializer(serializers.ModelSerializer):
    class Meta:
        model = IT80C
        fields = "__all__"


class OtherChapVIADeductionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherChapVIADeductions
        fields = "__all__"


class HouseRentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseRentInfo
        fields = "__all__"


class CreateHouseRentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseRentInfo
        exclude = ['it', 'house_rent_allowance']


class HouseRentAllowanceSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["house_rent_info"] = HouseRentInfoSerializer(instance.house_rent_info.all(), many=True).data
        return data

    class Meta:
        model = HouseRentAllowance
        fields = "__all__"


class MedicalSec80DSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalSec80D
        fields = "__all__"


class CreateMedicalSec80DSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalSec80D
        exclude = ("total_declared", "it")


class HousePropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseProperty
        fields = "__all__"


class CreateHousePropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseProperty
        exclude = ["it", "house_property_inc_loss"]


class HousePropertyIncomeLossSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['house_property'] = HousePropertySerializer(instance.house_property.all(), many=True).data
        return data

    class Meta:
        model = HousePropertyIncomeLoss
        fields = "__all__"


class CreateHousePropertyIncomeLossSerializer(serializers.ModelSerializer):
    class Meta:
        model = HousePropertyIncomeLoss
        exclude = ("house_property", "it")


class CreateOtherIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherIncome
        exclude = ("total_declared", "it")


class OtherIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherIncome
        fields = "__all__"


class GetITCalcSerializer(serializers.ModelSerializer):
    class Meta:
        model = IT
        fields = ["id", "old_reg_net_tax", "new_reg_net_tax", "old_reg_tax_inc", "new_reg_tax_inc", "selected_regime",
                  "business_inc"]


class SelectRegimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IT
        fields = ["business_inc", "selected_regime", "acknowledged"]


class GetITSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["it_80c"] = IT80CSerializer(instance.it_80c).data if instance.it_80c else None
        data["other_chap_vi_deductions"] = OtherChapVIADeductionsSerializer(
            instance.other_chap_vi_deductions).data if instance.other_chap_vi_deductions else None
        data["house_rent_allowance"] = HouseRentAllowanceSerializer(
            instance.house_rent_allowance).data if instance.house_rent_allowance else None
        data["medical_sec_80d"] = MedicalSec80DSerializer(
            instance.medical_sec_80d).data if instance.medical_sec_80d else None
        data["house_property_inc_loss"] = HousePropertyIncomeLossSerializer(
            instance.house_property_inc_loss).data if instance.house_property_inc_loss else None
        data["other_inc"] = OtherIncomeSerializer(instance.other_inc).data if instance.other_inc else None
        return data

    class Meta:
        model = IT
        fields = "__all__"


class CheckGetITSerializer(serializers.ModelSerializer):
    class Meta:
        model = IT
        fields = ["from_year", "to_year"]
