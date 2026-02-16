import io
import json
import time
from datetime import datetime

import requests


def login(username, password="Test1234"):
    url = "http://10.60.1.68/login"
    headers = {"Content-Type": "application/json"}
    data = {
        "username": username,
        "password": password,
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()


def get_desi_dept():
    url = "http://10.60.1.68/get_dept_desi"
    headers = {"Content-Type": "application/json"}
    response = requests.get(url, headers=headers)
    return response.json()


def get_all_candidate(token, page):
    url = "http://10.60.1.68/interview/candidate?page={0}&sort_field=&sort=".format(page)
    headers = {"Content-Type": "application/json", "Authorization": "Token {0}".format(token)}
    response = requests.get(url, headers=headers)
    return response.json()


def post_feedback(token, candidate_id, feedback, status, to_dept, tot_round):
    url = "http://10.60.1.68/interview/interview/create"
    headers = {"Content-Type": "application/json", "Authorization": "Token {0}".format(token)}
    form = {"candidate_id": candidate_id, "feedback": feedback, "status": status, "to_department": to_dept,
            "total_rounds": tot_round, }
    response = requests.post(url, json=form, headers=headers)
    return response.json()


def get_email_otp(email: str):
    url = "http://10.60.1.68/interview/send_email_otp"
    headers = {"Content-Type": "application/json"}
    form = {"email": email}
    response = requests.post(url, json=form, headers=headers)
    return response.json()


# TA = login(username="1111")
# HR = login(username="2222")
# CC = login(username="3333")
#
# # desi_dept = get_desi_dept()
#
# all_candidate = get_all_candidate(TA["token"], 1)
# candidate = all_candidate["results"][0]["id"]
#
# result = post_feedback(HR["token"], candidate, "Blah", "Selected For Next Round", "Human Resources", "3")
#
# print(candidate)

# print("\n\n", result)
# print(TA, HR, CC)

# interview/register

from faker import Faker


class PostTest:
    TOKEN = None
    DOMAIN = None
    HTTPS = False
    PATH = None

    show_failure = True

    headers = {"Content-Type": "application/json"}
    valid_data = {}
    tests = {}

    def __init__(self, domain, path, show_failure=True, valid_data=None, tests=None):
        if tests is None:
            tests = {}
        if valid_data is None:
            valid_data = {}
        self.DOMAIN = domain
        self.PATH = path
        self.valid_data = valid_data
        self.tests = tests
        self.show_failure = show_failure

    def set_https(self, is_https: bool):
        self.HTTPS = is_https

    def set_token(self, token: str):
        self.headers["Authorization"] = "Token {0}".format(token)

    def get_endpoint(self):
        return "{0}://{1}{2}".format("https" if self.HTTPS else "http", self.DOMAIN, self.PATH)

    def test(self):
        result = {'pass': 0, 'fail': 0, 'skipped': 0}
        for param in self.tests:
            cases = self.tests[param]
            if cases is None:
                result['skipped'] += 1
                continue
            for [value, error] in self.tests[param]:
                form = self.valid_data.copy()
                form[param] = value
                response = self.make_request(form)
                if response.get("error") == error:
                    result['pass'] += 1
                    print("[SUCCESS]", "[{0}]".format(param), "[TESTED: {0}]".format(value))
                    continue
                result['fail'] += 1
                if self.show_failure:
                    print("[FAIL]", "[{0}]".format(param), "[TESTED: {0}]".format(value),
                          "[Expected error: '{0}']".format(error), "[Received: {0}]".format(response))

        return result

    def make_request(self, form=None):
        headers = self.headers.copy()
        if form is None:
            form = {}
        files = {}
        for i in form.copy():
            if isinstance(form[i], io.BufferedReader):
                files.update({i: form[i]})
                del form[i]
        if len(form) > 0:
            headers.pop("Content-Type")
        response = requests.post(self.get_endpoint(), data=form, files=files, headers=headers)
        return response.json()


fake = Faker()

name = {
    "first_name": fake.first_name(),
    "middle_name": fake.first_name(),
    "last_name": fake.last_name(),
}

DATA = {
    "first_name": name["first_name"],
    "middle_name": name["middle_name"],
    "last_name": name["last_name"],
    "dob": str(fake.date_between_dates(date_start=datetime(1980, 1, 1), date_end=datetime(2004, 12, 31))),
    "email": "{0}.{1}@expertcallersdevtest.com".format(name["first_name"], name["last_name"]).lower(),
    "email_otp": "123456",
    "current_ctc": fake.pyfloat(1, 2, True),
    "expected_ctc": fake.pyfloat(1, 2, True),
    "total_work_exp": fake.random_number(1),
    "mobile": fake.numerify('#' * 10),
    "languages": "English",
    "source": "Walkin",
    "source_ref": fake.sentence(),
    "is_transport_required": fake.pybool(),
    "gender": fake.random_element(["Male", "Female", "Not Interested"]),
    "address": fake.address(),
    "prev_comp_exp": fake.random_number(2),
    "prev_comp_name": fake.company(),
    "aadhaar_no": fake.numerify('#' * 12),
    "branch": "HBR",
    'rsume': open('file.png', 'rb'),
    'relieving': open('file.png', 'rb'),
    "position_applied": "#B246D486BDD",
    "highest_qualification": "Graduate",
    "fields_of_experience": fake.random_elements(
        ["Payroll", "Full Stack", "Frontend", "Backend", "Power BI", "Data Scientist"])
}

TESTS = {
    "first_name": [("123", "first name: It Should Have Only Alpha Characters"),
                   ("#$#$#", "first name: It Should Have Only Alpha Characters"),
                   ("123#$#", "first name: It Should Have Only Alpha Characters"),
                   ("ABC123", "first name: It Should Have Only Alpha Characters"),
                   ("ABC##@#@$@", "first name: It Should Have Only Alpha Characters"),
                   ("", "first name: This Field May Not Be Blank."), (" ", "first name: This Field May Not Be Blank."),
                   ("\n", "first name: This Field May Not Be Blank.")],
    "middle_name": [("123", "middle name: It Should Have Only Alpha Characters"),
                    ("#$#$#", "middle name: It Should Have Only Alpha Characters"),
                    ("123#$#", "middle name: It Should Have Only Alpha Characters"),
                    ("ABC123", "middle name: It Should Have Only Alpha Characters"),
                    ("ABC##@#@$@", "middle name: It Should Have Only Alpha Characters"),
                    ("", "middle name: This Field May Not Be Blank."),
                    (" ", "middle name: This Field May Not Be Blank."),
                    ("\n", "middle name: This Field May Not Be Blank.")],
    "last_name": [("123", "last name: It Should Have Only Alpha Characters"),
                  ("#$#$#", "last name: It Should Have Only Alpha Characters"),
                  ("123#$#", "last name: It Should Have Only Alpha Characters"),
                  ("ABC123", "last name: It Should Have Only Alpha Characters"),
                  ("ABC##@#@$@", "last name: It Should Have Only Alpha Characters"),
                  ("", "last name: This Field May Not Be Blank."), (" ", "last name: This Field May Not Be Blank."),
                  ("\n", "last name: This Field May Not Be Blank.")],
    "dob": [("2005-31-01", "dob: Date Has Wrong Format. Use One Of These Formats Instead: Yyyy-Mm-Dd."),
            ("22-01-01", "dob: Date Has Wrong Format. Use One Of These Formats Instead: Yyyy-Mm-Dd."),
            ("2022-01-01", "dob: Candidate Must Be Greater Than 18 Years And Less Than 100 Years"),
            ("01-01-2000", "dob: Date Has Wrong Format. Use One Of These Formats Instead: Yyyy-Mm-Dd.")],
    "email": [("abc@gmail", "Invalid otp/email data, request for otp verification again"),
              ("@gmail.com", "Invalid otp/email data, request for otp verification again"),
              ("gmail.com", "Invalid otp/email data, request for otp verification again"),
              ("abc", "Invalid otp/email data, request for otp verification again"),
              ("abc@gmail", "Invalid otp/email data, request for otp verification again")],
    "email_otp": None,
    "current_ctc": [("abc", "current ctc: A Valid Number Is Required."),
                    ("!@!@", "current ctc: A Valid Number Is Required.")],
    "expected_ctc": [("abc", "expected ctc: A Valid Number Is Required."),
                     ("!@!@", "expected ctc: A Valid Number Is Required.")],
    "total_work_exp": [("abc", "total work exp: A Valid Number Is Required."),
                       ("!@!@", "total work exp: A Valid Number Is Required.")],
    "mobile": [("abc", "mobile number must be of length 10 digits"),
               ("!@!@", "mobile number must be of length 10 digits")],
    "languages": None,
    "source": [("abc", "source: \"Abc\" Is Not A Valid Choice."), ("!@!@", "source: \"!@!@\" Is Not A Valid Choice.")],
    "source_ref": None,
    "is_transport_required": [("abc", "is transport required: Must Be A Valid Boolean."),
                              ("!@!@", "is transport required: Must Be A Valid Boolean.")],
    "gender": [("abc", "gender: \"Abc\" Is Not A Valid Choice."), ("!@!@", "gender: \"!@!@\" Is Not A Valid Choice.")],
    "address": [("", "address: This Field May Not Be Blank.")],
    "rsume": None,
    "relieving": None,
    "prev_comp_exp": [("abc", "prev comp exp: It Mush Contain Only Numeric Data"),
                      ("!@!@", "prev comp exp: It Mush Contain Only Numeric Data")],
    "prev_comp_name": None,
    "aadhaar_no": [("abc", "Please provide valid aadhar number"), ("!@!@", "Please provide valid aadhar number")],
    "position_applied": [("abc", "please provide valid position applied data"),
                         ("!@!@", "please provide valid position applied data")],
    "highest_qualification": [("abc", "highest qualification: \"Abc\" Is Not A Valid Choice."),
                              ("!@!@", "highest qualification: \"!@!@\" Is Not A Valid Choice.")],
    "fields_of_experience": None,
}

import uuid


def create():
    Faker.seed(uuid.uuid4())
    name = {
        "first_name": fake.first_name(),
        "middle_name": fake.first_name(),
        "last_name": fake.last_name(),
    }
    nu = fake.random_number(5)
    return {
        "first_name": name["first_name"],
        "middle_name": name["middle_name"],
        "last_name": name["last_name"],
        "dob": str(fake.date_between_dates(date_start=datetime(1980, 1, 1), date_end=datetime(2004, 12, 31))),
        "email": "{0}.{1}.{2}.{3}@expertcallersdevtest.com".format(name["first_name"], name["middle_name"],
                                                                   name["last_name"],
                                                                   nu, ).lower(),
        "email_otp": "123456",
        "current_ctc": str(nu)[:3],
        "expected_ctc": str(nu)[:1],
        "total_work_exp": str(nu)[:2],
        "mobile": str(nu)[:1] * 10,
        "languages": "English",
        "source": "Walkin",
        "source_ref": fake.sentence(),
        "is_transport_required": fake.pybool(),
        "gender": fake.random_element(["Male", "Female", "Not Interested"]),
        "address": fake.address(),
        "prev_comp_exp": str(nu)[1]*2,
        "prev_comp_name": fake.company(),
        "aadhaar_no": fake.numerify('#' * 12),
        "branch": "HBR",
        'rsume': open('file.png', 'rb'),
        'relieving': open('file.png', 'rb'),
        "position_applied": "#B246D486BDD",
        "highest_qualification": "Graduate",
        "fields_of_experience": fake.random_elements(
            ["Payroll", "Full Stack", "Frontend", "Backend", "Power BI", "Data Scientist"])
    }


import multiprocessing


def register_a_mil():
    batch = 100
    count = 0
    start_time = datetime.now()
    total_times = []
    total_created = 0

    for i in range(1000000):
        try:
            d = create()
            candidate = PostTest(
                domain="10.60.1.68",
                path="/interview/register",
                valid_data=d,
                tests={'branch': [("HBR", "")]},
                show_failure=False
            )
            get_email_otp(d["email"])
            candidate.test()
            count += 1
            if count == batch:
                total_created += batch
                current_time = datetime.now()
                seconds = (current_time - start_time).total_seconds()
                start_time = current_time
                total_times.append(seconds)
                avg_seconds = sum(total_times) / len(total_times)
                count = 0
                print("{0} records created in {1}s. Avg seconds {2}s. Total records created {3}".format(batch, seconds,
                                                                                                        avg_seconds,
                                                                                                        total_created))
        except Exception as e:
            print("error = {0}".format(str(e)))
            continue


threads = []
for i in range(20):
    thread = multiprocessing.Process(target=register_a_mil)
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()

print("Done!")
#


# login_test = PostTest(
#     domain="10.60.1.68",
#     path="/interview/interview/create",
#     valid_data={"candidate_id": "539ba43033C", "feedback": "feedback", "status": "Selected For Next Round",
#                 "to_department": 2,
#                 "total_rounds": 2},
#     tests={
#         "candidate_id": [
#             ("sfsdfsd", "sfsdfsd is invalid, please provide the valid id")
#         ],
#         "feedback": None,
#         "status": [
#             ("aaa", "status: \"Aaa\" Is Not A Valid Choice.")
#         ],
#         "to_department": [
#             ("bbb", "bbb is invalid, please provide the valid department"),
#             (999999, "999999 is invalid, please provide the valid department")
#         ],
#         "total_rounds": [
#             ("-1", "total rounds: \"-1\" Is Not A Valid Choice.")
#         ],
#     },
# )
#
# ccfeedback_test = PostTest(
#     domain="10.60.1.68",
#     path="/interview/interview/create",
#     valid_data={"candidate_id": "539ba43033C", "feedback": "feedback", "status": "Selected For Next Round",},
#     tests={
#         "candidate_id": [
#             ("sfsdfsd", "sfsdfsd is invalid, please provide the valid id"),("@!#$%", "@!#$% is invalid, please provide the valid id")
#         ],
#         "feedback": None,
#         "status": [
#             ("aaa", " ")
#         ],
#     },
# )
#
# hrfeedback_test = PostTest(
#     domain="10.60.1.68",
#     path="/interview/interview/create",
#     valid_data={"candidate_id": "539ba43033C", "feedback": "feedback", "status": "Selected For Onboarding",},
#     tests={
#         "candidate_id": [
#             ("sfsdfsd", "sfsdfsd is invalid, please provide the valid id"),("@!#$%", "@!#$% is invalid, please provide the valid id")
#         ],
#         "feedback": None,
#         "to_department": None,
#         "status": [
#             ("Selected For Onboarding", " ")
#         ],
#     },
# )
#
# TA = login(username="1111")
# CC = login(username="4444")
# HR = login(username="2222")
# login_test.set_token(TA["token"])
# ccfeedback_test.set_token(CC["token"])
# hrfeedback_test.set_token(HR["token"])
#
# print(login_test.test())
# print(ccfeedback_test.test())
# print(hrfeedback_test.test())

# print(dir(fake))
