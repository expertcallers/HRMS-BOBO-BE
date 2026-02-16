from rest_framework import serializers
from .models import *
from mapping.serializer import *
from utils.utils import form_module_url, is_management


def form_document_url(doc_id):
    return form_module_url(doc_id, "article")


class CreateArticleSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        # Hash the password if provided
        raw_password = validated_data.pop('password', None)
        if raw_password:
            validated_data['password'] = make_password(raw_password)
        article = Article.objects.create(**validated_data)
        return article

    class Meta:
        model = Article
        exclude = ['is_active']


class CreateArticleVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleVersion
        exclude = ['documents', 'campaign', 'team', 'related_article', 'article', 'is_approved'
                   ]



class GetAllArticleVersionSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        user = self.context.get("user")
        has_view_access = self.context.get("has_view_access")
        data = super().to_representation(instance)
        data["added_by_emp_id"] = instance.added_by.emp_id if instance.added_by else None
        data["added_by_name"] = instance.added_by.full_name if instance.added_by else None
        data["name"] = instance.article.name if instance.article else None
        data["password"] = True if instance.article.password else False
        data["version"] = instance.version if instance else None
        data['start_date'] = instance.start_date if instance else None
        data['end_date'] = instance.end_date if instance else None
        if has_view_access == "management_articles" or instance.added_by.emp_id == user.emp_id:
            data["total_accepted"] = instance.total_accepted
            data["total_profiles"] = instance.total_profiles
        else:
            data["total_profiles"] = None
            data["total_accepted"] = None
        return data

    class Meta:
        model = ArticleVersion
        fields = ['id', 'created_at']


class ViewArticleSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = instance.article.name
        data['related_article'] = [
            {'id': article.id, 'name': article.article.name, 'password': True if article.article.password else False} for article
            in instance.related_article.all()]
        data["added_by_emp_id"] = instance.added_by.emp_id if instance.added_by else None
        data["added_by_name"] = instance.added_by.full_name if instance.added_by else None
        data["campaign"] = [
            {"id": cam.id, "name": cam.name} for cam in instance.campaign.all()
        ]
        data["team"] = [
            {"id": team.id, "name": team.name} for team in instance.team.all()
        ]
        data["documents"] = [
            {"id": doc.id, "name": doc.file.name.split("/")[::-1][0], "path": form_document_url(doc.id)} for doc in
            instance.documents.all()
        ]
        return data

    class Meta:
        model = ArticleVersion
        fields = "__all__"


class GetAllArticleUserCommentSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_id"] = instance.added_by.emp_id if instance.added_by else None
        data["emp_name"] = instance.added_by.full_name if instance.added_by else None
        data["emp_image"] = settings.MEDIA_URL + str(
            instance.added_by.image) if instance.added_by and instance.added_by.image else None
        data[
            "emp_gender"] = instance.added_by.onboard.gender if instance.added_by and instance.added_by.onboard else None
        return data

    class Meta:
        model = ArticleUserComment
        exclude = ['added_by', 'article']


class ArticleUserCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleUserComment
        fields = '__all__'


class ArticleUserResponseApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleUserResponse
        exclude = ['comment']


class NotificationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context.get('user')
        user_notification = UserNotification.objects.filter(notification=instance, profile=user).first()
        data["is_read"] = user_notification.is_read if user_notification else None
        return data

    class Meta:
        model = Notifications
        exclude = ['team', 'campaign']


class UserNotificationApiSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["notification"] = NotificationSerializer(instance.notification).data
        data["is_read"] = instance.is_read
        return data

    class Meta:
        model = UserNotification
        fields = ["notification", "is_read"]


class ArticleVoteSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["total_is_favourite"] = ArticleUserResponse.objects.filter(article=instance.article,
                                                                        is_favourite=True).count()
        data["total_is_upvote"] = ArticleUserResponse.objects.filter(article=instance.article, is_upvote=True).count()

        return data

    class Meta:
        model = ArticleUserResponse
        fields = ['id', 'is_upvote', 'is_favourite', 'is_acknowledged']


class AcknowledgedResponseSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_id"] = instance.profile.emp_id if instance.profile else None
        data["emp_name"] = instance.profile.full_name if instance.profile else None

        return data

    class Meta:
        model = ArticleUserResponse
        fields = ["is_acknowledged"]

class GetAllArticleVersionHisSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        user = self.context.get("user")
        data = super().to_representation(instance)
        data["added_by_emp_id"] = instance.added_by.emp_id if instance.added_by else None
        data["added_by_name"] = instance.added_by.full_name if instance.added_by else None
        data["name"] = instance.article.name if instance.article else None
        data["password"] = True if instance.article.password else False
        data["version"] = instance.version if instance else None
        data['start_date'] = instance.start_date if instance else None
        data['end_date'] = instance.end_date if instance else None
        data["is_active"]=True if instance.article.active_version and instance.article.active_version.id == instance.id else False
        if instance.added_by.emp_id == user.emp_id:
            data["total_accepted"] = instance.total_accepted
            data["total_profiles"] = instance.total_profiles
        else:
            data["total_profiles"] = None
            data["total_accepted"] = None
        return data

    class Meta:
        model = ArticleVersion
        fields = ['id', 'created_at']