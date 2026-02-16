from django.urls import path
from report import views

urlpatterns = [
    path("import_bigo_sla", views.import_bigo_sla, name="import_bigo_sla"),
    path("import_bigo_ta", views.import_bigo_ta, name="import_bigo_ta"),
    path("import_tiya_sla", views.import_tiya_sla, name="import_tiya_sla"),
    path("import_tiya_ta", views.import_tiya_ta, name="import_tiya_ta"),
    path("import_gbm_reports/<str:report_name>", views.import_gbm_reports, name="import_gbm_reports"),
    path("import_insalvage_report", views.import_insalvage, name="import_insalvage_report"),
    path("import_aadhya_reports/<str:call_type>", views.import_aadhya_reports, name="import_aadhya_reports"),
    path("import_medicare_report", views.import_medicare, name="import_medicare_report"),
    path("import_sapphire_medical_reports", views.import_sapphire_medical_reports,
         name="import_sapphire_medical_reports"),
    path("import_capgemini_report", views.import_capgemini_report, name="import_capgemini_report"),
    path("get_all_reports_files", views.GetAllReportsFiles.as_view(), name="get_all_reports_files"),
    path("get_my_reports_files", views.GetMyReportsFile.as_view(), name="get_my_reports_files"),
    path("delete_report_file/<str:report_id>", views.delete_report_file, name="delete_report_file"),
    path('import_bbm_report', views.import_bbm_report, name="import_bbm_report")
]
