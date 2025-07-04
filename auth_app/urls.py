# auth_app/urls.py

from django.urls import path, include
from . import views
from . import api_views
from rest_framework.routers import DefaultRouter

# --- API uchun router sozlamalari ---
router = DefaultRouter()
router.register(r'admin/tests', api_views.AdminTestViewSet, basename='admin-test')
router.register(r'admin/results', api_views.AdminResultsViewSet, basename='admin-result')

# API URL'lari
api_urlpatterns = [
    # Talaba API'lari
    path('tests/', api_views.TestListView.as_view(), name='api-test-list'),
    path('tests/<int:pk>/', api_views.TestDetailView.as_view(), name='api-test-detail'),
    path('responses/<int:pk>/submit/', api_views.TestSubmitView.as_view(), name='api-test-submit'),
    path('results/', api_views.TestResultListView.as_view(), name='api-result-list'),
    
    # Admin API'lari (Router orqali)
    path('', include(router.urls)),
]

# Asosiy URL'lar (Veb-sahifalar uchun)
urlpatterns = [
    # Mavjud URL'lar
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('', views.home_view, name='home'),

    # --- Test tizimi uchun yangi veb URL'lar ---
    path('tests/', views.TestListView.as_view(), name='test-list'),
    path('tests/<int:pk>/', views.TestDetailView.as_view(), name='test-detail'),
    path('tests/<int:test_id>/take/', views.take_test_view, name='test-take'),
    path('results/<int:pk>/', views.TestResultDetailView.as_view(), name='test-result-detail'),
    
    # API yo'nalishlarini qo'shish
    path('api/v1/', include((api_urlpatterns, 'auth_app'), namespace='api')),
]