from rest_framework import status

from utils.util_classes import BaseAPITest


# Create your tests here.

class TestPayroll(BaseAPITest):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setUpTestData()

    def test_get_all_variable_pay(self):
        response = self.mgmt.get('/payroll/get_all_variable_pay')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.manager.get('/payroll/get_all_variable_pay')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.agent.get('/payroll/get_all_variable_pay')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_all_ecpl_employee_payroll(self):
        response = self.mgmt.get('/payroll/get_all_ecpl_employee_payroll')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_get_all_variable_pay_to_be_approved(self):
    #     response = self.mgmt.get('/payroll/get_all_variable_pay_to_be_approved')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_salary_structure(self):
        response = self.mgmt.post('/payroll/get_salary_structure', data={"total_fixed_gross": 20000, "pay_grade": "L1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_variable_pay_approve_count(self):
    #     response = self.mgmt.get('/payroll/variable_pay_approve_count')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(type(response.data['Pending_Variable_Pay']), type(1))

    def test_view_all_salary(self):
        response = self.client.get('/payroll/view_all_salary')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.ta.get('/payroll/view_all_salary')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
