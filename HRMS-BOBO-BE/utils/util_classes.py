import logging
import unittest

from django.db import models
from datetime import datetime, timedelta

from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework import exceptions, status
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from hrms import settings
from utils.utils import tz, article_validate_token, authenticate_article_token

logger = logging.getLogger(__name__)


class CustomTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token. Please try logging in again'))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        return (token.user, token)

    def authenticate(self, request):
        # logger.info("custom authentication")
        user_token = super().authenticate(request)
        if not user_token:
            # logger.info("came here {0}".format(user_token))
            return user_token
        user, token = user_token
        last_activity_at = user.last_activity_at
        now = timezone.now()
        token_obj = Token.objects.filter(user=user).last()
        token_created = token_obj.created

        diff = now - token_created
        if diff.total_seconds() > 3600 * 10:
            if token_obj:
                token_obj.delete()
                token = None

        user.last_activity_at = now
        user.save()
        if not token:
            return None

        return user, token


class CustomTokenArticleAuthentication(CustomTokenAuthentication):
    def authenticate(self, request):
        user_token = super().authenticate(request)
        authenticate_article_token(request)
        return user_token


base_api_test_class = None


def client_login(username):
    api_client = APIClient()
    response = api_client.post('/mapping/login', {'username': username, 'password': f'Ecpl@{username}'})
    # assertEqual(response.status_code, status.HTTP_200_OK)
    if response.status_code != 200:
        raise AssertionError("Failed to login")
    token = response.data['token']
    # self.client.content_type = 'application/json'
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    return api_client


class BaseAPITest(unittest.TestCase):
    mgmt, manager, agent, hr, ta, client = [None] * 6

    @classmethod
    def setUpTestData(cls):
        # mgmt,manager,agent,hr,ta
        if cls.mgmt is None:
            # print("came initializing")
            accounts = settings.TEST_ACCOUNTS

            cls.mgmt = client_login(accounts[0])
            cls.manager = client_login(accounts[1])
            cls.agent = client_login(accounts[2])
            cls.hr = client_login(accounts[3])
            cls.ta = client_login(accounts[4])
            cls.client = client_login(accounts[5])
            # print("clients initialised")
        else:
            pass
            # print("using initialized")
