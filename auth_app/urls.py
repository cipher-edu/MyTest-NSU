# auth_app/urls.py

from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from . import views 
from . import api_views
from .views import *
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('', views.home_view, name='home'),

]
