from django.contrib import admin

from utils.utils import get_column_names_with_foreign_keys_separate
from .models import *


class DocumentInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        Document)
    search_fields = list_display.copy()
    list_display += foreign_keys


class ArticleInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        Article)
    search_fields = list_display.copy()
    list_display += foreign_keys


class ArticleVersionInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        ArticleVersion)
    search_fields = list_display.copy()
    list_display += foreign_keys


class ArticleUserResponseInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        ArticleUserResponse)
    search_fields = list_display.copy()
    list_display += foreign_keys


class ArticleUserCommentInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        ArticleUserComment)
    search_fields = list_display.copy()
    list_display += foreign_keys


class NotificationsInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        Notifications)
    search_fields = list_display.copy()
    list_display += foreign_keys


class UserNotificationInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        UserNotification)
    search_fields = list_display.copy()
    search_fields += ["profile__emp_id"]
    list_display += foreign_keys


admin.site.register(Document, DocumentInfo)
admin.site.register(Article, ArticleInfo)
admin.site.register(ArticleVersion, ArticleVersionInfo)
admin.site.register(ArticleUserResponse, ArticleUserResponseInfo)
admin.site.register(Notifications, NotificationsInfo)
admin.site.register(UserNotification, UserNotificationInfo)
admin.site.register(ArticleUserComment, ArticleUserCommentInfo)
