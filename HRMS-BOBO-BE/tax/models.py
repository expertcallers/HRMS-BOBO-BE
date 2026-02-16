from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models

from hrms import settings
from mapping.models import Profile


# Create your models here.
def validate_year(val):
    year = datetime.today().year - 1
    if not int(val) >= year:
        raise ValidationError("Year must be same or greater than previous year")


class IT80C(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_it80c_f")
    total_declared = models.BigIntegerField(blank=True, null=True)
    fixed_dep_5y_sch_bnk = models.BigIntegerField(blank=True, null=True)
    children_tuition_fee = models.BigIntegerField(blank=True, null=True)
    cont_pension_fund = models.BigIntegerField(blank=True, null=True)
    deposit_nsc = models.BigIntegerField(blank=True, null=True)
    deposit_nss = models.BigIntegerField(blank=True, null=True)
    deposit_post_off_sav_scheme = models.BigIntegerField(blank=True, null=True)
    equity_linked_sav_scheme = models.BigIntegerField(blank=True, null=True)
    interest_nsc_reinvested = models.BigIntegerField(blank=True, null=True)
    life_ins_premium = models.BigIntegerField(blank=True, null=True)
    long_term_infra_bonds = models.BigIntegerField(blank=True, null=True)
    mutual_funds = models.BigIntegerField(blank=True, null=True)
    nabard_rural_bonds = models.BigIntegerField(blank=True, null=True)
    nat_pension_scheme = models.BigIntegerField(blank=True, null=True)
    nhb_scheme = models.BigIntegerField(blank=True, null=True)
    post_off_time_dep_5y = models.BigIntegerField(blank=True, null=True)
    pradan_man_surak_bima_yoj = models.BigIntegerField(blank=True, null=True)
    public_prov_fund = models.BigIntegerField(blank=True, null=True)
    repay_housing_loan = models.BigIntegerField(blank=True, null=True)
    stamp_duty_regi_charges = models.BigIntegerField(blank=True, null=True)
    suk_sam_yojana = models.BigIntegerField(blank=True, null=True)
    unit_link_ins_premium = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class OtherChapVIADeductions(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_other_chap4a_dec_f")
    total_declared = models.BigIntegerField(blank=True, null=True)
    add_int_80ee_house_loan_bor_1apr2016 = models.BigIntegerField(blank=True, null=True)  # //
    add_int_80eea_house_loan_bor_1apr2019 = models.BigIntegerField(blank=True, null=True)
    vi_80ggc_donations_political_party = models.BigIntegerField(blank=True, null=True)
    vi_80gga_donations_scientific_research = models.BigIntegerField(blank=True, null=True)
    emp_cont_nps_80ccd_1 = models.BigIntegerField(blank=True, null=True)
    int_ele_veh_bor_1apr2019_80eeb = models.BigIntegerField(blank=True, null=True)
    cont_nps_2015_80ccd1_b = models.BigIntegerField(blank=True, null=True)
    int_dep_sav_acc_fd_po_co_so_sen_cit_80ttb = models.BigIntegerField(blank=True, null=True)
    vi_10_10b_retrenchment_compensation = models.BigIntegerField(blank=True, null=True)
    super_exem_10_13 = models.BigIntegerField(blank=True, null=True)
    donation_100perc_exemp_80g = models.BigIntegerField(blank=True, null=True)
    donation_50perc_exemp_80g = models.BigIntegerField(blank=True, null=True)
    donation_child_edu_80g = models.BigIntegerField(blank=True, null=True)
    donation_pol_part_80g = models.BigIntegerField(blank=True, null=True)
    donation_int_dep_sav_acc_fd_po_co_so_80tta = models.BigIntegerField(blank=True, null=True)
    int_loan_high_self_edu_80e = models.BigIntegerField(blank=True, null=True)
    med_treat_ins_hand_dep_80dd = models.BigIntegerField(blank=True, null=True)
    med_treat_ins_hand_dep_sev_80dd = models.BigIntegerField(blank=True, null=True)
    med_treat_spec_dis_80ddb = models.BigIntegerField(blank=True, null=True)
    med_treat_spec_dis_sen_citi_80ddb = models.BigIntegerField(blank=True, null=True)
    perm_phy_dis_abov_80perc_80u = models.BigIntegerField(blank=True, null=True)
    perm_phy_dis_btw_40_80perc_80u = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class HouseRentInfo(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_house_rent_info_dec_f")
    house_rent_allowance = models.ForeignKey('tax.HouseRentAllowance', on_delete=models.CASCADE,
                                             related_name="house_rent_info_allowance")
    start_date = models.CharField(max_length=8)
    end_date = models.CharField(max_length=8)
    monthly_rent_amount = models.BigIntegerField()
    annual_rent_amount = models.BigIntegerField()
    address_1 = models.CharField(max_length=255, blank=True, null=True)
    address_2 = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    ll_address_1 = models.CharField(max_length=255, blank=True, null=True)  # ll land_lord
    ll_address_2 = models.CharField(max_length=255, blank=True, null=True)
    ll_state = models.CharField(max_length=255, blank=True, null=True)
    ll_city = models.CharField(max_length=255, blank=True, null=True)
    ll_zip_code = models.CharField(max_length=10, blank=True, null=True)
    landlord_name = models.CharField(max_length=255, blank=True, null=True)
    landlord_pan = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class HouseRentAllowance(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_house_rent_allowance_f")
    total_declared = models.BigIntegerField()
    house_rent_info = models.ManyToManyField(HouseRentInfo, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class MedicalSec80D(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_medical_sec_80d_f")
    total_declared = models.BigIntegerField(blank=True, null=True)
    medical_bil_sen_cit = models.BigIntegerField(blank=True, null=True)
    prev_hlth_checkup = models.BigIntegerField(blank=True, null=True)
    prev_hlth_checkup_dependant_parents = models.BigIntegerField(blank=True, null=True)
    medical_ins_pre_age = models.CharField(max_length=8, choices=settings.AGE_80D)
    medical_ins_pre_amount = models.BigIntegerField(blank=True, null=True)
    medical_ins_pre_dep_parents_age = models.CharField(max_length=8, choices=settings.AGE_80D)
    medical_ins_pre_dep_parents_amount = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.id)


class HouseProperty(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_house_property_f")
    house_property_inc_loss = models.ForeignKey("tax.HousePropertyIncomeLoss", on_delete=models.CASCADE,
                                                related_name="it_house_property_inc_loss")
    annual_letable_val_rent_rec = models.BigIntegerField(blank=True, null=True)
    less_mun_taxs_paid_during_year = models.BigIntegerField(blank=True, null=True)
    less_unrealized_rent = models.BigIntegerField(blank=True, null=True)
    net_value = models.BigIntegerField(blank=True, null=True)
    std_ded_at_30perc_net_annual_val = models.BigIntegerField(blank=True, null=True)
    int_on_house_loan = models.BigIntegerField(blank=True, null=True)
    lenders_name = models.CharField(max_length=255, blank=True, null=True)
    lenders_pan = models.CharField(max_length=10, blank=True, null=True)
    income_loss_from_let_out_property = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.id)


class HousePropertyIncomeLoss(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_house_property_income_loss_f")
    total_exemption = models.BigIntegerField(default=0)
    int_housing_loan_self_occupied = models.BigIntegerField(default=0)
    tot_inc_loss_frm_let_out_property = models.BigIntegerField(default=0)

    inc_frm_self_ocu_prpty_intr_house_loan = models.BigIntegerField()
    inc_frm_self_ocu_prpty_lender_name = models.CharField(max_length=255, blank=True, null=True)
    inc_frm_self_ocu_prpty_lender_pan = models.CharField(max_length=10, blank=True, null=True)

    house_property = models.ManyToManyField(HouseProperty, blank=True)

    def __str__(self):
        return str(self.id)


class OtherIncome(models.Model):
    it = models.ForeignKey("tax.IT", on_delete=models.CASCADE, related_name="it_other_income_f")
    total_declared = models.BigIntegerField(blank=True, null=True)
    oth_inc_1_particulars = models.CharField(max_length=255, blank=True, null=True)
    oth_inc_1_declared_amount = models.BigIntegerField(blank=True, null=True)
    oth_inc_2_particulars = models.CharField(max_length=255, blank=True, null=True)
    oth_inc_2_declared_amount = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.id)


class IT(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="it_payroll_profile", blank=True,
                                null=True)
    from_year = models.CharField(max_length=4, validators=[validate_year])
    to_year = models.CharField(max_length=4, validators=[validate_year])
    declaration_date = models.DateTimeField(blank=True, null=True)
    it_80c = models.ForeignKey(IT80C, on_delete=models.SET_NULL, blank=True, null=True, related_name="it_80c_it")
    other_chap_vi_deductions = models.ForeignKey(OtherChapVIADeductions, on_delete=models.SET_NULL, blank=True,
                                                 null=True, related_name="other_chap_4_it")
    house_rent_allowance = models.ForeignKey(HouseRentAllowance, on_delete=models.SET_NULL, blank=True, null=True,
                                             related_name="house_rent_all_it")
    medical_sec_80d = models.ForeignKey(MedicalSec80D, on_delete=models.SET_NULL, blank=True, null=True,
                                        related_name="medical_sec_it")
    house_property_inc_loss = models.ForeignKey(HousePropertyIncomeLoss, on_delete=models.SET_NULL, blank=True,
                                                null=True, related_name="house_property_inc")
    other_inc = models.ForeignKey(OtherIncome, on_delete=models.SET_NULL, blank=True, null=True,
                                  related_name="other_inc")
    old_reg_net_tax = models.FloatField(blank=True, null=True)
    new_reg_net_tax = models.FloatField(blank=True, null=True)
    old_reg_tax_inc = models.FloatField(blank=True, null=True)
    new_reg_tax_inc = models.FloatField(blank=True, null=True)
    selected_regime = models.CharField(max_length=10, choices=settings.TAX_REGIME, blank=True, null=True)
    business_inc = models.CharField(max_length=3, choices=settings.YES_NO, blank=True, null=True)
    acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.profile)
