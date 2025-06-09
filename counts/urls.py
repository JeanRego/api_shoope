from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import home,excluir_titulo

urlpatterns = [
    path('', home, name='home'),
    path('excluir/<int:id>/', excluir_titulo, name='excluir_titulo'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
