from django.urls import path
from .views import recommend_category

urlpatterns = [
    path('recommend/', recommend_category, name='recommend_category'),
]
