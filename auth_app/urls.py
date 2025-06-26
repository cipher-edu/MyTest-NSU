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

    # Talabalar uchun
    path('tests/', views.test_list_view, name='test_list'),
    path('tests/<int:pk>/', views.test_detail_view, name='test_detail'),
    path('tests/<int:test_id>/start/', views.start_attempt_view, name='start_attempt'),
    path('tests/attempt/<int:attempt_id>/', views.take_test_view, name='take_test'),
    path('tests/attempt/<int:attempt_id>/finish/', views.finish_attempt_view, name='finish_attempt'),
    path('tests/result/<int:attempt_id>/', views.attempt_result_view, name='attempt_result'),

    # O'qituvchilar uchun
    path('manage/tests/', views.TestListView.as_view(), name='teacher_test_list'),
    path('manage/tests/create/', views.TestCreateView.as_view(), name='test_create'),
    path('manage/tests/<int:pk>/update/', views.TestUpdateView.as_view(), name='test_update'),
    path('manage/tests/<int:pk>/delete/', views.TestDeleteView.as_view(), name='test_delete'),
    path('manage/tests/<int:test_id>/questions/', views.manage_questions_view, name='manage_questions'),
]