from django.core.management.base import BaseCommand
from ams.tasks import sync_users_from_turnstile

class Command(BaseCommand):
    help = "Sync users from source turnstile to others"

    def handle(self, *args, **kwargs):
        sync_users_from_turnstile()
        self.stdout.write(self.style.SUCCESS("✅ User sync completed"))



