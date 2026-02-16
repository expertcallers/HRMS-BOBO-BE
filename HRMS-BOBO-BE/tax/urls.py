from django.urls import path
from tax import views

urlpatterns = [
    path("get_it_declaration", views.get_it_declaration),
    path("initiate_it_declaration", views.initiate_it_declaration),
    path("create_update_80c/<str:it_id>", views.create_update_80c),
    path("create_update_other_chap_vi_deductions/<str:it_id>", views.create_update_other_chap_vi_deductions),
    path("create_update_house_rent_allowance/<str:it_id>", views.create_update_house_rent_allowance),
    path("create_update_medical_sec_80d/<str:it_id>", views.create_update_medical_sec_80d),
    path("create_update_house_property_income_loss/<str:it_id>", views.create_update_house_property_income_loss),
    path("create_update_other_income/<str:it_id>", views.create_update_other_income),
    path("calculate_tax/<str:it_id>", views.calculate_tax),
    path("get_tax_calc/<str:it_id>", views.get_tax_calc),
    path("select_regime/<str:it_id>", views.select_regime)
]
