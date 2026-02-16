import json
import traceback

from team.models import Team
from .models import *
from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from datetime import datetime
from django.db.models import Q, Max, Count, Case, When, IntegerField
from rest_framework.permissions import IsAuthenticated
from mapping.views import HasUrlPermission
from rest_framework import status
from django.contrib.auth.hashers import check_password
from utils.sort_and_filter_by_cols import get_sort_and_filter_by_cols
from utils.utils import return_error_response, hash_file, document_response, is_management, create_notification, \
    assigning_notification, article_validate_token, authenticate_article_token, is_manager_and_above, \
    check_if_method_has_url_access
from .serializers import *
import logging
from django.contrib.auth.hashers import check_password
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.http import HttpResponse
from utils.util_classes import CustomTokenAuthentication, CustomTokenArticleAuthentication
from django.db.models import F, Value
from django.db.models.functions import Concat

logger = logging.getLogger()


class ArticleApi(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated,
                          ]
    serializer_class = GetAllArticleVersionSerializer
    model = serializer_class.Meta.model

    def get_serializer_context(self):
        # Add the user to the serializer context
        context = super().get_serializer_context()
        context["user"] = self.request.user
        context["has_view_access"] = self.request.resolver_match.view_name
        return context

    def get(self, request, *args, **kwargs):
        try:
            team = request.user.team
            mapped = {'name':'article__name'}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=mapped)
            logger.info(f"order_by_cols- {order_by_cols},search_query-{search_query},filter_by-{filter_by}")
            view_name = request.resolver_match.view_name
            active_articles = Article.objects.filter(is_active=True).values_list('active_version', flat=True)
            if view_name == "management_articles":
                check_if_method_has_url_access(request, self)
                self.queryset = ArticleVersion.objects.filter(id__in=active_articles).filter(
                    Q(start_date__lte=datetime.now().date()) & (Q(end_date__gte=datetime.now().date()) | Q(
                        end_date__isnull=True)) & Q(is_approved=True)
                ).filter(search_query).filter(
                    **filter_by).annotate(
                    total_accepted=Count('article_response', filter=Q(article_response__is_acknowledged=True),distinct=True),
                    total_profiles=Count("team__team", filter=Q(team__team__status="Active"), distinct=True)
                ).order_by(*order_by_cols)
            else:
                self.queryset = ArticleVersion.objects.filter(id__in=active_articles).filter(
                    Q(start_date__lte=datetime.now().date()) & (Q(end_date__gte=datetime.now().date()) | Q(
                        end_date__isnull=True)) & Q(team__id=team.id) & Q(
                        is_approved=True)
                ).filter(
                    search_query).filter(**filter_by).annotate(
                    total_accepted=Count('article_response', filter=Q(article_response__is_acknowledged=True),distinct=True),
                    total_profiles=Count("team__team", filter=Q(team__team__status="Active"), distinct=True)
                ).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info(f"exception at get_all_article {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            article_id = data.get("article_id")
            article_name = data.get("name")
            related_articles = data.getlist("related_article")
            logger.info(f"Article post data {data}")
            category = data.get("category")
            data["added_by"] = request.user.id
            content = data.get("content")
            files = request.FILES.getlist("documents", [])
            team = data.getlist("team")
            campaigns = data.getlist("base_team")
            article_serializer = CreateArticleSerializer(data=data)
            if not article_serializer.is_valid():
                return_error_response(article_serializer, raise_exception=True)
            article_version_serializer = CreateArticleVersionSerializer(data=data)
            if not article_version_serializer.is_valid():
                return_error_response(article_version_serializer, raise_exception=True)
            message = 'Process update created successfully'
            article = None
            if article_id:
                # update
                article_version = ArticleVersion.objects.filter(id=article_id).first()
                if article_version is None:
                    raise ValueError("Invalid Process update id is provided")
                article = article_version.article
            token = ""
            if article:
                # update is creation of new version of the current article
                authenticate_article_token(request, article_id=article_id)
                latest_version = ArticleVersion.objects.filter(article__id=article.id).last().version
                article_version_serializer.validated_data["version"] = latest_version + 1

            else:
                article = Article.objects.filter(name=article_name).first()
                if article:
                    raise ValueError(
                        f'Please provide new process update name, "{article_name}" already exists')
                # article creation
                article = article_serializer.create(article_serializer.validated_data)
                if article.password:
                    token = self.generate_token(article)

            article_version_serializer.validated_data["article"] = article
            article_version_obj = article_version_serializer.create(article_version_serializer.validated_data)
            article.active_version = article_version_obj
            article.save()

            related_articles = [item.strip() for item in related_articles]
            if related_articles and related_articles != [''] and isinstance(related_articles, list):
                article_version_obj.related_article.set(related_articles)

            if (team and isinstance(team, list)) or category.lower() == "general":
                if category.lower() == "general":
                    teams = list(Team.objects.filter(is_active=True).values_list('id', flat=True))
                else:
                    teams = team
                article_version_obj.team.set(teams)

            if (campaigns and isinstance(campaigns, list)) or category.lower() == "general":
                if category.lower() == "general":
                    campaigns = list(Process.objects.filter(is_active=True).values_list('id', flat=True))
                else:
                    campaigns = campaigns
                article_version_obj.campaign.set(campaigns)

            for file in files:
                file_hash_val = hash_file(file)
                doc = article_version_obj.documents.filter(file_hash=file_hash_val).first()
                if not doc:
                    new_doc = Document.objects.create(file=file, file_hash=file_hash_val, added_by=request.user)
                    article_version_obj.documents.add(new_doc)

            # create notification for the article
            article_link = f"/hrms/article/authenticate/{article_version_obj.id}"
            notification_obj = create_notification(f"{article.name} v{article.active_version.version}",
                                                   f"{article.get_plain_text()}"[:255], article_link,
                                                   team=article.active_version.team.all(),
                                                   campaign=article.active_version.campaign.all())
            assigning_notification(notification_obj,article_version_obj.added_by)

            return Response({"message": message, "article_id": article.active_version.id, "token": token},
                            status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f"exception at post_article {traceback.format_exc(5)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        """
        Override this method to apply permissions only to specific methods.
        """
        if self.request.method == 'POST':
            return [HasUrlPermission(), IsAuthenticated()]
        return []  # No permissions for GET or other methods

    def generate_token(self, article, validity_minutes=1440):
        if not article.article_token or timezone.now() > article.token_expires_at:
            token = str(uuid.uuid4())  # Generate a unique token when there is no token or token expire
            article.set_token(token, validity_minutes)  # Save token and set expiry
        else:
            token = article.article_token
        return token


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_related_articles(request):
    try:
        article_name = request.query_params.get("article_name")
        related_articles = list(
            ArticleVersion.objects.filter(article__name__istartswith=article_name, is_approved=True).annotate(
                name_with_version=Concat(
                    F('article__name'),
                    Value(' - v'),
                    F('version'),
                    output_field=models.CharField()  # Ensure the output is treated as a string
                )).values_list('id', 'name_with_version', named=True))

        return HttpResponse(json.dumps({"result": related_articles}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class ViewArticleApi(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenArticleAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ViewArticleSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            return Response({'article': self.serializer_class(request.article).data})
        except Exception as e:
            logger.info(f"exception at view_article {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_document(request, doc_id):
    return document_response(Document, doc_id)


class ArticleUserResponseApi(GenericAPIView, ListModelMixin):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenArticleAuthentication]
    serializer_class = GetAllArticleUserCommentSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            article = request.article
            mapped = {}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=mapped)
            logger.info(f"order_by_cols- {order_by_cols},search_query-{search_query},filter_by-{filter_by}")
            self.queryset = ArticleUserComment.objects.filter(article__id=article.id).filter(
                search_query).filter(**filter_by).order_by(
                *order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info(f"exception at get article_responses {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        try:
            article = request.article

            profile = request.user
            data = request.data.copy()
            data["article"] = article.id
            data["profile"] = profile.id
            is_comment = data.get("comment")
            logger.info(f"Article user response data {data}")
            article_user_obj = ArticleUserResponse.objects.filter(article__id=article.id, profile=profile).first()
            serializer = ArticleUserResponseApiSerializer(data=data)
            if not serializer.is_valid():
                return_error_response(serializer, raise_exception=True)
            if not article_user_obj:
                article_user_obj = serializer.create(serializer.validated_data)
            else:
                serializer.update(article_user_obj, serializer.validated_data)
            if is_comment:
                data = {'comment': data.get("comment"), 'added_by': request.user.id, 'article': article.id}
                article_comment_serializer = ArticleUserCommentSerializer(data=data)
                if not article_comment_serializer.is_valid():
                    return_error_response(article_comment_serializer, raise_exception=True)
                comment_obj = article_comment_serializer.create(article_comment_serializer.validated_data)
                article_user_obj.comment.add(comment_obj)
            message = 'User Response captured successfully'
            return Response({'message': message}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.info(f'exception at post user_article_response')
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ArticleVersionHistory(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated,
                          # HasUrlPermission
                          ]
    serializer_class = GetAllArticleVersionHisSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            active_version_id = kwargs.get("article_id")
            article_version = ArticleVersion.objects.filter(id=active_version_id).first()
            if article_version is None:
                raise ValueError("Invalid Process update id is provided")
            mapped = {}
            profile = request.user
            team = request.user.team
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=mapped)
            logger.info(f"order_by_cols- {order_by_cols},search_query-{search_query},filter_by-{filter_by}")
            if profile.designation.department.dept_id in ["cc"] or is_manager_and_above(profile):

                self.queryset = ArticleVersion.objects.filter(article__id=article_version.article.id).filter(
                    is_approved=True
                ).filter(search_query).filter(
                    **filter_by).annotate(
                    total_accepted=Count('article_response', filter=Q(article_response__is_acknowledged=True),distinct=True),
                    total_profiles=Count("team__team", filter=Q(team__team__status="Active"), distinct=True)
                ).order_by(*order_by_cols)

            else:
                self.queryset = ArticleVersion.objects.filter(article__id=article_version.article.id).filter(
                    Q(team__id=team.id) & Q(
                        is_approved=True)
                ).filter(
                    search_query).filter(**filter_by).annotate(
                    total_accepted=Count('article_response', filter=Q(article_response__is_acknowledged=True),distinct=True),
                    total_profiles=Count("team__team", filter=Q(team__team__status="Active"), distinct=True)
                ).order_by(*order_by_cols)

            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info(f"exception at article_version_history {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_context(self):
        # Add the user to the serializer context
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context


class NotificationApi(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated,
                          # HasUrlPermission
                          ]
    serializer_class = NotificationSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            profile = request.user
            notification_ids = UserNotification.objects.filter(profile=profile,is_read=False).values_list('notification', flat=True)
            mapped = {}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=mapped)
            self.queryset = Notifications.objects.filter(id__in=notification_ids).filter(
                search_query).filter(**filter_by).order_by(
                *order_by_cols)

            return self.list(request, *args, **kwargs)

        except Exception as e:
            logger.info(f"exception at get_notification {traceback.format_exc(5)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_context(self):
        # Add the user to the serializer context
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

    def post(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            logger.info(f"notification data {data}")
            profile = request.user
            notification_ids = data.get("notification_ids")
            user_notifications = UserNotification.objects.filter(notification__id__in=notification_ids, profile=profile)
            if not user_notifications:
                raise ValueError('Invalid notification ids is provided')
            user_notifications.update(is_read=True)
            message = 'Notification updated successfully'
            return Response({}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.info(f"exception at notification_post {traceback.format_exc(5)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ArticleVote(GenericAPIView, ListModelMixin):
    permission_classes = [IsAuthenticated]
    authentication_classes = [
        CustomTokenArticleAuthentication]
    serializer_class = ArticleVoteSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            article = request.article
            article_id = article.id
            profile = request.user
            article_response = ArticleUserResponse.objects.filter(article__id=article_id, profile=profile).first()
            total_favourite = ArticleUserResponse.objects.filter(article__id=article_id, is_favourite=True).count()
            total_upvote = ArticleUserResponse.objects.filter(article__id=article_id, is_upvote=True).count()

            if article_response:
                logger.info(f"article vote get {self.serializer_class(article_response).data}")
                return Response({'article': self.serializer_class(article_response).data})
            else:
                data = {'is_upvote': None, 'is_favourite': None, "total_is_favourite": total_favourite,
                        "total_is_upvote": total_upvote}
                logger.info(f"article vote get {data}")
                return Response({'article': data})

        except  Exception as e:
            logger.info(f"exception at get article_vote {traceback.format_exc(5)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ArticleBookmarks(GenericAPIView, ListModelMixin):
    permission_classes = [IsAuthenticated]
    authentication_classes = [
        CustomTokenAuthentication]
    serializer_class = GetAllArticleVersionSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            profile = request.user
            bookmarked_article_ids = ArticleUserResponse.objects.filter(is_favourite=True, profile=profile).values_list(
                'article', flat=True)
            mapped = {'name':'article__name'}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=mapped)
            logger.info(f"filter_by : {filter_by},search_query : {search_query},order_by_cols : {order_by_cols}")
            self.queryset = ArticleVersion.objects.filter(id__in=bookmarked_article_ids).filter(
                search_query).filter(**filter_by).annotate(
                    total_accepted=Count('article_response', filter=Q(article_response__is_acknowledged=True),distinct=True),
                    total_profiles=Count("team__team", filter=Q(team__team__status="Active"), distinct=True)
                ).order_by(*order_by_cols)

            return self.list(request, *args, **kwargs)

        except Exception as e:
            logger.info(f"exception at get bookmarks {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_context(self):
        # Add the user to the serializer context
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context


class ArticleAuthenticate(GenericAPIView, ListModelMixin):
    permission_classes = [IsAuthenticated]
    authentication_classes = [
        CustomTokenAuthentication]

    def post(self, request, *args, **kwargs):
        try:
            article_id = kwargs.get("article_id")
            password = request.data.get("password")

            article = ArticleVersion.objects.filter(id=article_id).first()
            article_password = article.article.password
            if not article:
                raise ValueError("Invalid Process update id is provided")
            token = ""
            if article_password:
                if not check_password(password, article_password):
                    raise ValueError('Invalid password.')

                token = self.generate_token(article.article)

            return Response({"token": token})

        except Exception as e:
            logger.info(f"exception at post authenticate_article {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def generate_token(self, article, validity_minutes=1440):
        if not article.article_token or timezone.now() > article.token_expires_at:
            token = str(uuid.uuid4())  # Generate a unique token when there is no token or token expire
            article.set_token(token, validity_minutes)  # Save token and set expiry
        else:
            token = article.article_token
        return token


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def requires_password(request, article_id):
    try:
        article = ArticleVersion.objects.filter(id=article_id).first()
        return Response({'password': True if article and article.article.password else False})

    except Exception as e:
        logger.info(f"exception at get bookmarks {traceback.format_exc(5)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AcknowledgedProfiles(GenericAPIView, ListModelMixin):
    permission_classes = [IsAuthenticated, HasUrlPermission]
    authentication_classes = [
        CustomTokenAuthentication]
    serializer_class = AcknowledgedResponseSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            article_id = kwargs.get("article_id")
            logger.info(f"GET {request.GET}")
            mapped = {'employee':'profile'}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=mapped)
            self.queryset = ArticleUserResponse.objects.filter(article__id=article_id).filter(
                search_query).filter(**filter_by).order_by(
                *order_by_cols)
            return self.list(request, *args, **kwargs)

        except Exception as e:
            logger.info(f"exception at get bookmarks {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActivateArticle(GenericAPIView, ListModelMixin):
    permission_classes = [IsAuthenticated, HasUrlPermission]
    authentication_classes = [CustomTokenAuthentication]

    def patch(self, request, *args, **kwargs):
        try:
            article_id = kwargs.get("article_id")
            article_version = ArticleVersion.objects.filter(id=article_id).first()
            if not article_version:
                raise ValueError("Invalid Process update id is provided")
            article = article_version.article
            if article:
                article.active_version = article_version
                article.save()
            message = f"{article.name} v- {article_version.version} is activated successfully"
            logger.info(message)
            return Response({'message': message}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f"exception at activate article updation {traceback.format_exc(5)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
