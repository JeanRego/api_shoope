from rest_framework import serializers
from .models import CategoryRequest

class CategoryRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryRequest
        fields = ['id', 'title', 'category_id', 'requested_at']
        read_only_fields = ['id', 'category_id', 'requested_at']
