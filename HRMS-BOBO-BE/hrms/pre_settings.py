from datetime import datetime

FRONT_END_VERSION = "1.1.15"
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework.authtoken',
    'rest_framework',
    'corsheaders',
    "training_room",
    "mirage",
    'import_export',
    'ckeditor',
    'po',
    'headcount',
    'powerbi',
    'interview_test',
    'faq',
    'exit',
    'ticketing',
    'asset',
    'interview',
    'mapping',
    'onboarding',
    'ams',
    'erf',
    "payroll",
    "team",
    "ijp",
    "appraisal",
    "it",
    "tax",
    "article",
    "transport"
]
SECOND_DB_APPS = [
    'report'
]
INSTALLED_APPS += SECOND_DB_APPS
SERVER_PUBLIC_FILE_SAVE_ENDPOINT = "http://10.60.1.68:9002/api/interview/save_file_from_public_server"
# SERVER_PUBLIC_FILE_SAVE_ENDPOINT = "https://hrms.expertcallers.in/api/interview/save_file_from_public_server"
# 'openai',
# 'ask_emma'
ATT_EXC_ALLOWED = False  # Set it to True if dates need to be excluded
ATT_EXC_DATE = datetime.today().replace(year=2023, month=12, day=4).date()
ATT_EXC_START_DATE = datetime.today().replace(year=2023, month=11, day=29).date()
ATT_EXC_END_DATE = datetime.today().replace(year=2023, month=11, day=30).date()
PROF_TAX_LIMIT = 25000
ESI_LIMIT = 21000  # ECPL
PF_GROSS_LIMIT = 15000
PF_FIXED_DEDUCTION_AMOUNT = 1800
PAY_GRADE_LEVELS = [("L1", "Level 1"), ("L2", "Level 2"), ("L3", "Level 3"), ("L4", "Level 4"), ("L5", "Level 5"),
                    ("L6", "Level 6"), ("L7", "Level 7"), ("L8", "Level 8"), ("L9", "Level 9")]
QUESTION_TYPE = [("single", "single"), ("multiple", "multiple"), ("text", "text"), ("essay", "essay")]
EMPLOYEE_REFERRAL_STATUS = [("Referred", "Referred"), ("Interview", "Interview"), ("Employee", "Employee"),
                            ("Rejected", "Rejected")]
DEFAULT_ALLOWED_EXTENSIONS = ['webp', 'png', 'jpeg', 'pdf', 'jpg', 'docx']
ONBOARD_ALLOWED_EXTENSIONS = ['webp', 'png', 'jpeg', 'pdf', 'jpg']
AMS_SCHEDULE_CORRECTION = [("Week Off", "Week Off"), ('Scheduled', "Scheduled")]
ERF_HISTORY_STATUS = [("Linked", "Linked"), ("Unlinked", "Unlinked")]
LANG_CHOICES = ['English', 'Hindi', 'Marathi', 'Gujarati', 'Kannada', 'Tamil', 'Malayalam', 'Bengali', 'Telugu',
                'Arabic']
GENDER_CHOICES = [("Male", "Male"), ("Female", "Female"), ("Not Interested", "Not Interested")]
MARITAL_STATUS = [("Single", "Single"), ("Married", "Married"), ("Widowed", "Widowed"), ("Divorced", "Divorced")]
CANDIDATE_STATUS_CHOICES = [("Not Applied", "Not Applied"), ('Applied', "Applied"),
                            ('Selected For Next Round', "Selected For Next Round"),
                            ("Selected for Final TA Round", "Selected for Final TA Round"),
                            ('Selected For Onboarding', "Selected For Onboarding"),
                            ('Viewed', "Viewed"), ('Selected', "Selected"), ('Onboard', "Onboard"),
                            ('Rejected', "Rejected"), ('Hold', "Hold"), ('Active', "Active"), ('Reopen', "Reopen"),
                            ("Attrition", "Attrition"), ("Bench", "Bench"), ("NCNS", "NCNS"),
                            ("Terminated", "Terminated")]
PROFILE_STATUS = [("Active", "Active"), ("Attrition", "Attrition"), ("Bench", "Bench"), ("NCNS", "NCNS"),
                  ("Terminated", "Terminated")]
READONLY_PROFILE_STATUS = [("Terminated", "Terminated")]
QUALF_CHOICES = [("Matriculation", 'Matriculation'), ('Pre University', "Pre University"), ('Graduate', "Graduate"),
                 ('Post Graduate', "Post Graduate"), ('Other', "Other")]
SOURCE_CHOICES = [("Migration", "Migration"), ('Walkin', 'Walkin'), ('Referral', "Referral"),
                  ('Consultancy', "Consultancy"), ('Social Media', "Social Media"), ('Job Portal', 'Job Portal'),
                  ('Other', 'Other')]
SOURCE_READ_ONLY = ["Migration"]
BRANCH_CHOICES = [("HBR Layout", "HBR Layout"), ("Kothnur", "Kothnur")]
ERF_APPROVAL_LIMIT = 50000
MISC_FIELDS = [("appointment_letter_content", "Appointment Letter Content"), ("status", "Status"),
               ("qualification", "Qualification"), ("source", "Source"), ("gender", "Gender"),
               ("process_type_one", "Process Type One"), ("process_type_two", "Process Type Two"),
               ("process_type_three", "Process Type Three"), ("selection_criteria", "Selection Criteria"),
               ("selection_process", "Selection Process")]

TEAM_DESI_MAPPING_FIELDS = [("manager", "Manager"), ("asst_manager", "Assistant Manager"),
                            ("team_leader", "Team Leader"), ("tl_am_manager", "All Team Leader to CEO")]
MISC_MINI_FIELDS = [("erf_approval_limit", "ERF Approval Limit")]

DESI_DONOT_REQUIRES_VP_APPROVAL = ["CRO", "Client Relationship Officer", "Patrolling Officer"]
ATTENDANCE_STATUS = [("Absent", "Absent"), ("Present", "Present"), ("PL", "Paid Leave"), ("SL", "Sick Leave"),
                     ("Week Off", "Week Off"), ('Scheduled', "Scheduled"), ("Comp Off", "Comp Off"), ("ML", "ML"),
                     ("Half Day", "Half Day"), ("NCNS", "NCNS"), ("NH", "National Holiday"),
                     ("Unscheduled", "Unscheduled"), ("Client Off", "Client Off"), ("Bench", "Bench"),
                     ("Training", "Training"), ("Attrition", "Attrition")]
MARK_ATTENDANCE_STATUS = [("Absent", "Absent"), ("Present", "Present"), ("Week Off", "Week Off"),
                          ("Comp Off", "Comp Off"), ("Half Day", "Half Day"), ("NCNS", "NCNS"),
                          ("Client Off", "Client Off"), ("Training", "Training"), ("Scheduled", "Scheduled")]
DIRECT_ATTENDANCE_MARK_STATUS = [("Absent", "Absent"), ("Present", "Present"), ("PL", "Paid Leave"), ("SL", "Sick Leave"),
                     ("Week Off", "Week Off"), ('Scheduled', "Scheduled"), ("Comp Off", "Comp Off"), ("ML", "ML"),
                     ("Half Day", "Half Day"), ("NCNS", "NCNS"), ("NH", "National Holiday"),
                     ("Unscheduled", "Unscheduled"), ("Client Off", "Client Off"), ("Bench", "Bench"),
                     ("Training", "Training")]
MARK_ATTENDANCE_NON_HR_READ_ONLY = ["Attrition", "Bench"]
AMS_MARK_HOLIDAY = [("Client Off", "Client Off")]
NOT_FOR_MARK_ATTENDANCE = ["PL", "SL", "Scheduled"]
LEAVE_STATUS = [("Withdrawn", "Withdrawn"), ("Approved", "Approved"), ("Rejected", "Rejected"), ("Pending", "Pending")]
READ_ONLY_LEAVE_STATUS = ["Pending", "Withdrawn"]
LEAVE_TYPES = [("PL", "Paid Leave"), ("SL", "Sick Leave")]
BLOOD_GROUP = [("A+", "A+"), ("A-", "A-"), ("AB+", "AB+"), ("AB-", "AB-"), ("B+", "B+"), ("B-", "B-"), ("O+", "O+"),
               ("O-", "O-"), ("A1+", "A1+"), ("A2+", "A2+"), ("A1-", "A1-"), ("A2-", "A2-")]

REQUISITION_TYPE = [("Buffer", "Buffer"), ("Replacement", "Replacement"), ("Budgeted", "Budgeted")]
TYPE_OF_WORKING = [("Rotational", "Rotational"), ("Fixed", "Fixed")]
SHIFT_TIMING = [("Rotational", "Rotational"), ("Fixed", "Fixed")]
ERF_APPROVAL_STATUS = [("Approved", "Approved"), ("Rejected", "Rejected"), ("Pending", "Pending")]
AMS_CORRECTION_STATUS = ERF_APPROVAL_STATUS
AMS_CORRECTION_READ_ONLY_STATUS = [("Pending", "Pending")]
AMS_MARK_ATT_CORRECTION_READ_ONLY_STATUS = [("Training", "Training"), ("Scheduled", "Scheduled")]
READONLY_ERF_APPROVAL_STATUS = ["Pending"]
AGE_80D = [("<60", "<60"), ("60 to 79", "60 to 79"), (">=80", ">=80")]
FINANCIAL_YEARS = [["2024", "2025"]]  # TODO Handle it properly

IJP_CANDIDATE_STATUS = [("Selected", "Selected"), ("Rejected", "Rejected"),
                        ("Selected for Next Round", "Selected for Next Round"), ("Applied", "Applied")]
IJP_SHIFT_TIMING = [("Rotational Shift", "Rotational Shift"), ("Morning Shift", "Morning Shift"),
                    ("Day Shift", "Day Shift"), ("Night Shift", "Night Shift")]
MAPPING_STATUS = [("Approved", "Approved"), ("Pending", "Pending"), ("Rejected", "Rejected")]
RESIGNATION_STATUS = [("Withdrawn", "Withdrawn"), ("Approved", "Approved"), ("Rejected", "Rejected"),
                      ("Pending", "Pending"), ("Terminated", "Terminated")]
READ_ONLY_RESIGNATION_STATUS = [("Withdrawn", "Withdrawn"), ("Pending", "Pending"), ("Terminated", "Terminated")]
SATISFACTION_LEVEL = [("Very Satisfied", "Very Satisfied"), ("Satisfied", "Satisfied"), ("Neutral", "Neutral"),
                      ("Dissatisfied", "Dissatisfied"), ("Very Dissatisfied", "Very Dissatisfied")]
EXIT_FEEDBACK_RATING = [("Excellent", "Excellent"), ("Good", "Good"), ("Fair", "Fair"), ("Poor", "Poor"),
                        ("Very Poor", "Very Poor")]
EXIT_FORM_CHOICES = [("Yes", "Yes"), ("No", "No"), ("NA", "NA")]
TRAINING_FEEDBACK_RATING = [("Yes, completely", "Yes, completely"), ("Yes, to some extent", "Yes, to some extent"),
                            ("No, not really", "No, not really")]
TICKET_STATUS_CHOICES = [("Open", "Open"), ("Closed", "Closed"), ("On Hold", "On Hold"), ("Resolved", "Resolved"),
                         ("Spam", "Spam")]
READONLY_TICKET_STATUS_CHOICES = [("Open", "Open"), ("Resolved", "Resolved"), ("Closed", "Closed")]
TICKET_PRIORITY = [("High", "High"), ("Low", "Low"), ("Normal", "Normal"), ("Urgent", "Urgent")]

ASSET_ALLOCATION_CHOICES = [("Issued", "Issued"), ("Returned", "Returned")]
ASSET_STATUS = [("Assigned", "Assigned"), ("Spare", "Spare"), ("Under Repair", "Under Repair"),
                ("Archived", "Archived"), ("Available", "Available"),
                ("Pending Return", "Pending Return"), ("Reserved", "Reserved")]
READONLY_ASSET_STATUS = [("Assigned", "Assigned")]
HARD_DISK_TYPE = [("HDD", "HDD"), ("SSD", "SSD")]
INTERVIEW_TEST_STATUS = [("Started", "Started"), ("Completed", "Completed"), ("Force Completed", "Force Completed")]
MANAGER_AND_ABOVE = ["Manager", "Management", "VP"]
PO_OFFICE_CHOICES = [("Kothanur Office", "Kothanur Office"), ("HBR Office", "HBR Office")]
PO_BILLING_OFFICE = "HBR Office"
PO_OFFICE_ADDRESS = {"HBR Office": "# 1877/4, HBR Layout, 2nd Block 1st Stage, 80ft Main Road, Bangalore - 560043",
                     "Kothanur Office": "Indraprastha, No.81, Survey No.11, Gubbi cross, Kothanur PO, Hennur - Bagalur Main Road, Bengaluru - 560077"}
DELIVERY_OFFICE = "Expert Callers Solutions Pvt Ltd"
PO_CATEGORY = [("Capex", "Capex"), ("Opex", "Opex")]
PASS_PREFIX = "Ecpl@"  # passprefixNEWEMPID
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 10  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 10  # 10 MB
HEADCOUNT_HOURS = 8
HEADCOUNT_STATUS_CHOICES = ERF_APPROVAL_STATUS
HEADCOUNT_STATUS_READONLY_CHOICES = AMS_CORRECTION_READ_ONLY_STATUS
HC_CURRENCY = [("USD", "USD"), ("Rupee", "Rupee"), ("GBP", "GBP"), ("AUD", "AUD"), ("CAD", "CAD")]
HC_PRICING_TYPE = [("FTE", "FTE"), ("Hourly", "Hourly")]

PROCESS_TYPE = [("Inbound Standard", "Inbound Standard"), ("Outbound Standard", "Outbound Standard"),
                ("Other", "Other")]
DATA_SOURCE = [("Client Portal", "Client Portal"), ("Dialer", "Dialer"), ("Dumps", "Dumps"), ("Email", "Email"),
               ("Google Doc", "Google Doc")]
SOP_STATUS = [("Pending", "Pending"), ("Completed", "Completed")]

CHANGE_MGMT_TYPE = [("Emergency", "Emergency"), ("Standard", "Standard"), ("Major", "Major"), ("Normal", "Normal")]
APPLICATION_SYSTEM = [("System", "System"), ("VM", "VM"), ("Firewall", "Firewall"), ("Application", "Application")]
CHANGE_IMPACT = [("IT Infrastructure", "IT Infrastructure"), ("CDE Infrastructure", "CDE Infrastructure")]
DEVICE_NAME = [("FortiGate 400E", "FortiGate 400E"), ("FortiGate 600E", "FortiGate 600E"),
               ("IBM eServer x3400-[7973PAA]", "IBM eServer x3400-[7973PAA]"),
               ("IBM System X3250 M4", "IBM System X3250 M4"), ("Dell PowerEdge R510", "Dell PowerEdge R510"),
               ("Dell PowerEdge R630", "Dell PowerEdge R630"), ("Dell Poweredge R710", "Dell Poweredge R710"),
               ("Dell PowerEdge R720", "Dell PowerEdge R720")]
CHANGE_SITE = [("Prod", "Prod"), ("Non-Prod", "Non-Prod")]
CHANGE_STATUS = [("Accepted", "Accepted"), ("Rejected", "Rejected"), ("Pending", "Pending")]
APPRAISAL_STATUS = [("Appraisal Completed", "Appraisal Completed"),
                    ("Parameters Added", "Parameters Added"),
                    ("Self Appraisal In Progress", "Self Appraisal In Progress"),
                    ("Self Appraisal Completed", "Self Appraisal Completed"),
                    ("Manager Appraisal In Progress", "Manager Appraisal In Progress"),
                    ("Manager Appraisal Completed", "Manager Appraisal Completed")]
TEST_RESULT = [("Pass", "Pass"), ("Fail", "Fail")]
ARTICLE_CATEGORIES = [("Campaign specific", "Campaign specific"), ("General", "General")]

# TAX_MAX_VALUES = {"max_it_80c":150000,""}
# Income tax max values
INCOME_TAX_MAX_VALUES = {"it_80c": 150000,
                         "add_int_80ee_house_loan_bor_1apr2016": 50000,
                         "add_int_80eea_house_loan_bor_1apr2019": 150000,
                         "vi_80ggc_donations_political_party": 99999999,
                         "vi_80gga_donations_scientific_research": 99999999,
                         "emp_cont_nps_80ccd_1": 150000,
                         "int_ele_veh_bor_1apr2019_80eeb": 150000,
                         "cont_nps_2015_80ccd1_b": 50000,
                         "int_dep_sav_acc_fd_po_co_so_sen_cit_80ttb": 50000,
                         "vi_10_10b_retrenchment_compensation": 500000,
                         "super_exem_10_13": 150000,
                         "donation_100perc_exemp_80g": 99999999,
                         "donation_50perc_exemp_80g": 99999999,
                         "donation_child_edu_80g": 99999999,
                         "donation_pol_part_80g": 99999999,
                         "donation_int_dep_sav_acc_fd_po_co_so_80tta": 10000,
                         "int_loan_high_self_edu_80e": 99999999,
                         "med_treat_ins_hand_dep_80dd": 75000,
                         "med_treat_ins_hand_dep_sev_80dd": 125000,
                         "med_treat_spec_dis_80ddb": 40000,
                         "med_treat_spec_dis_sen_citi_80ddb": 100000,
                         "perm_phy_dis_abov_80perc_80u": 125000,
                         "perm_phy_dis_btw_40_80perc_80u": 75000,
                         "medical_bil_sen_cit": 50000,
                         "prev_hlth_checkup": 5000,
                         "prev_hlth_checkup_dependant_parents": 5000,
                         "medical_ins_pre_amount": 25000,
                         "medical_ins_pre_dep_parents_amount": 25000}

SPECIFIC_DISEASES = ["Dementia", "Dystonia Musculorum Deformans", "Motor Neuron Disease", "Ataxia", "Chorea",
                     "Hemiballismus", "Aphasia", "Parkinsons Disease", "Malignant Cancers",
                     "Full Blown Acquired Immuno-Deficiency Syndrome (AIDS)", "Chronic Renal failure",
                     "Hematological disorders"]
TAX_REGIME = [("Old Regime", "Old Regime"), ("New Regime", "New Regime")]
YES_NO = [("Yes", "Yes"), ("No", "No")]

SALARY_UPDATE_REASON = [("Onboard", "Onboard"), ("Appraisal", "Appraisal"), ("Promotion", "Promotion"),
                        ("Process Change", "Process Change")]

INTERN_POSITION = [("Frontend", "Frontend"), ("Backend", "Backend"), ("Tester", "Tester")]
TRANSPORT_APPROVAL_STATUS = [("Approved", "Approved"), ("Rejected", "Rejected")]
TRANSPORT_APPROVAL_STATUS_ALL = [("Approved", "Approved"), ("Rejected", "Rejected"), ("Pending", "Pending"),
                                 ("NA", "NA")]

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True
