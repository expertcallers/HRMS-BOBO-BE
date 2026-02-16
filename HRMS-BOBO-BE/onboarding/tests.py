# Create your tests here.
from rest_framework import status

from utils.util_classes import BaseAPITest

from datetime import datetime

today = datetime.today().date()


class TestAMS(BaseAPITest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setUpTestData()

    def test_get_all_onboard(self):
        response = self.manager.get('/onboard/get')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data['results']) > 0:
            first_id = response.data["results"][0]
            response = self.manager.get(f'/onboard/get/{first_id["id"]}')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
