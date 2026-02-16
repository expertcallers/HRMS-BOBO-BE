from ckeditor.fields import RichTextField
from crum import get_current_user
from django.db import models

from mapping.models import Profile


# Create your models here.
class FAQDocuments(models.Model):
    file = models.FileField()
    file_name = models.CharField(max_length=255, blank=True, null=True)
    added_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                 related_name="faq_file_added_by")

    def save(self, *args, **kwargs):
        user = get_current_user()

        user = user if user else None
        if self.file:
            self.file_name = self.file.name
            self.added_by = user
        super(FAQDocuments, self).save(*args, **kwargs)


class FAQ(models.Model):
    question = models.CharField(max_length=400)
    answer = RichTextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class GenericRichTextData(models.Model):
    title = models.CharField(max_length=400)
    content = RichTextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)
