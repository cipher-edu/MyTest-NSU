# auth_app/urls.py
from django.urls import path, include
from . import views, api_views
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import action

app_name = 'auth_app'

# --- API uchun router ---
router = DefaultRouter()
router.register(r'admin/tests', api_views.AdminTestViewSet, basename='admin-test')
router.register(r'admin/results', api_views.AdminResultsViewSet, basename='admin-result')

# --- API manzillari ---
api_urlpatterns = [
    # Talaba API'lari (to'g'ri nomlar bilan)
    path('tests/', api_views.TestListViewAPI.as_view(), name='api-test-list'),
    path('tests/<int:pk>/', api_views.TestDetailViewAPI.as_view(), name='api-test-detail'),
    path('responses/<int:pk>/submit/', api_views.TestSubmitViewAPI.as_view(), name='api-test-submit'),
    path('results/', api_views.TestResultListViewAPI.as_view(), name='api-result-list'),
    
    # Admin API'lari (Router orqali)
    path('', include(router.urls)),
]

# --- Veb-sahifalar uchun manzillar ---
urlpatterns = [
    # Autentifikatsiya
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Test tizimi
    path('tests/', views.TestListView.as_view(), name='test-list'),
    path('tests/<int:pk>/', views.TestDetailView.as_view(), name='test-detail'),
    path('tests/<int:test_id>/take/', views.take_test_view, name='take-test'),
    path('submit-test/<int:response_id>/', views.submit_test_view, name='submit-test'),
    path('test-results/', views.TestResultListView.as_view(), name='test-result-list'),
    path('test-results/<int:pk>/', views.TestResultDetailView.as_view(), name='test-result-detail'),

    # Bosh sahifa
    path('', views.home_view, name='home'),
]