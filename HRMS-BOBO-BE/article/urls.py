from django.urls import path
from .views import *

urlpatterns = [
    path("article", ArticleApi.as_view(), name="create_article"),
    path("management_articles", ArticleApi.as_view(), name="management_articles"),
    path("view_article/<str:article_id>", ViewArticleApi.as_view()),
    path("get_related_articles", get_related_articles),
    path("article_version_history/<str:article_id>", ArticleVersionHistory.as_view()),
    path('document/<str:doc_id>', get_document),
    path("article_response/<str:article_id>", ArticleUserResponseApi.as_view()),
    path("notification", NotificationApi.as_view()),
    path("article_vote/<str:article_id>", ArticleVote.as_view()),
    path('bookmarks', ArticleBookmarks.as_view()),
    path('authenticate/<str:article_id>', ArticleAuthenticate.as_view()),
    path("requires_password/<str:article_id>", requires_password),
    path("acknowledged_profiles/<str:article_id>", AcknowledgedProfiles.as_view(), name="acknowledged_profiles"),
    path("activate/<str:article_id>", ActivateArticle.as_view(), name="activate_article")
]
