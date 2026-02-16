from django.core.management.base import BaseCommand
from ams.tasks import fetch_and_store_attendance  # adjust import to match your app

class Command(BaseCommand):
    help = 'Fetch attendance logs from biometric device'

    def handle(self, *args, **kwargs):
        fetch_and_store_attendance()
