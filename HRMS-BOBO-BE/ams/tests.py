# Create your tests here.
from rest_framework import status

from team.models import Process, Team
from utils.util_classes import BaseAPITest

from datetime import datetime

today = datetime.today().date()


class TestAMS(BaseAPITest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setUpTestData()

    def test_get_team_self_leave_history(self):
        response = self.manager.get('/ams/get_team_self_leave_history')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_GetAllLeaveHistory(self):
        response = self.manager.get('/ams/get_all_leave_history')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_GetMyAttendanceSchedule(self):
        response = self.manager.get('/ams/get_my_schedule')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_applied_leaves(self):
        response = self.manager.get('/ams/get_all_applied_leaves/0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.manager.get('/ams/get_all_applied_leaves/1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_applied_leaves_count(self):
        response = self.manager.get('/ams/get_all_applied_leaves_count/0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.manager.get('/ams/get_all_applied_leaves_count/1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_leave_balance(self):
        response = self.manager.get('/ams/get_leave_balance')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_my_leave_balance_history(self):
        response = self.manager.get('/ams/get_my_leave_balance_history')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_team_members_emp_ids(self):
        response = self.manager.get('/ams/get_team_members_emp_ids')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_attendance(self):
        response = self.manager.post('/ams/get_attendance/5638',
                                     data={'start_date': f"{today.replace(day=1)}", 'end_date': f"{today}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_team_schedule(self):
        response = self.manager.get('/ams/get_team_schedule')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_team_approval_schedule(self):
        response = self.manager.get('/ams/get_team_approval_schedule/0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.manager.get('/ams/get_team_approval_schedule/1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_unmarked_attendance_count(self):
        response = self.manager.get('/ams/get_all_unmarked_attendance_count/0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.manager.get('/ams/get_all_unmarked_attendance_count/1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_leave_balance_history(self):
        response = self.manager.get('/ams/get_all_leave_balance_history')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_attend_login_status(self):
        response = self.manager.get('/ams/get_attend_login_status')
        if response.status_code == 400:
            self.assertEqual(response.data['error'], 'There is No schedule exists for this date')
        else:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_att_cor_req(self):
        response = self.manager.get('/ams/get_all_att_cor_req/0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.manager.get('/ams/get_all_att_cor_req/1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_attendance_correction_count(self):
        response = self.manager.get('/ams/get_all_attendance_correction_count/0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.manager.get('/ams/get_all_attendance_correction_count/1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_attend_cor_req_history(self):
        response = self.manager.get('/ams/attend_cor_req_history')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_att_live_stats(self):
        response = self.manager.get('/ams/get_att_live_stats')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_team_break(self):
        response = self.manager.get('/ams/get_all_team_break')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_team_att_report(self):
        today = datetime.today().date()
        # response = self.manager.post('/ams/download_team_att_report',
        #                              data={"team": "__all_", "start_date": str(today), "end_date": str(today)})
        #
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response.data[:4], "date")

    def test_download_all_att_report(self):
        today = datetime.today().date()
        # process = Process.objects.filter(name="CC Team").first()
        # team = Team.objects.filter(base_team=process).first()
        # response = self.manager.post('/ams/download_all_att_report',
        #                              data={"team": team.id, "base_team": process, "start_date": str(today),
        #                                    "end_date": str(today)})
        # if response.status_code not in [200, 201]:
        #     print(response.data)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(response.data[:3], "EID")
