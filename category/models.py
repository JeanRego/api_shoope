from django.db import models

class CategoryRequest(models.Model):
    title = models.CharField(max_length=255)
    category_id = models.IntegerField(null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
