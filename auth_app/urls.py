# auth_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Mavjud URL'lar
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('', views.home_view, name='home'),

    # --- Test tizimi uchun yangi URL'lar ---

]