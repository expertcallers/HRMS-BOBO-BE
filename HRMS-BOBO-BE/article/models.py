import logging
import uuid
from ckeditor.fields import RichTextField
from django.db import models
from hrms import settings
from mapping.models import Department
from team.models import Process, Team
from datetime import datetime, timedelta
from mapping.models import Profile
from django.utils.html import strip_tags
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

logger = logging.getLogger()


def document_file(instance, filename):
    today = datetime.today()
    return '/'.join(
        ['documents', str(today.year), str(today.month), str(today.day), str(uuid.uuid4()), filename])


class Document(models.Model):
    file = models.FileField(upload_to=document_file)
    file_hash = models.CharField(max_length=32, blank=True, null=True)
    added_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="article_document")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Document {self.file}"


class Article(models.Model):
    name = models.CharField(max_length=255)
    active_version = models.ForeignKey('article.ArticleVersion', on_delete=models.SET_NULL, null=True,
                                       related_name="active_version")
    password = models.CharField(max_length=128, blank=True, null=True)
    article_token = models.CharField(max_length=250, blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    added_by = models.ForeignKey(Profile, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_plain_text(self):
        return strip_tags(self.active_version.content) if self.active_version else ""

    def set_token(self, token, validity_minutes=1440):
        """
        Generate a token and set its expiry time for one day.
        """
        self.article_token = token
        self.token_expires_at = datetime.now() + timedelta(minutes=validity_minutes)
        self.save()

    def __str__(self):
        return f"{self.id} - {self.name} -v {self.active_version.version if self.active_version else ''}"


class ArticleVersion(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="article_versions")
    category = models.CharField(max_length=20, choices=settings.ARTICLE_CATEGORIES)
    campaign = models.ManyToManyField(Process, related_name="article_campaigns", blank=True)
    team = models.ManyToManyField(Team, related_name='article_teams', blank=True)
    version = models.PositiveIntegerField(default=1)
    is_approved = models.BooleanField(default=True)
    content = RichTextField()
    documents = models.ManyToManyField(Document, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    related_article = models.ManyToManyField('self', blank=True)
    added_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="article_version_added_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.article.name} -v {self.version}"


class ArticleUserComment(models.Model):
    added_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_comments")
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    article = models.ForeignKey(ArticleVersion, on_delete=models.CASCADE, related_name="article_comment")
    # def __str__(self):
    #     return self.id


class ArticleUserResponse(models.Model):
    article = models.ForeignKey(ArticleVersion, on_delete=models.CASCADE, related_name="article_response")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_response")
    comment = models.ManyToManyField(ArticleUserComment, null=True, blank=True)
    is_upvote = models.BooleanField(null=True, blank=True)
    is_favourite = models.BooleanField(null=True, blank=True)
    is_acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Response of {self.profile} for {self.article}"


class Notifications(models.Model):
    title = models.CharField(max_length=250)
    message = models.TextField(null=True, blank=True)
    link = models.CharField(max_length=500, blank=True, null=True)
    team = models.ManyToManyField(Team, related_name='notification_teams', blank=True)
    campaign = models.ManyToManyField(Process, related_name="notification_process", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"


class UserNotification(models.Model):
    notification = models.ForeignKey(Notifications, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"User {self.profile} 's {self.notification}"
