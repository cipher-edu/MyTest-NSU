# external_auth_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Admin paneli uchun manzil
    path('admin/', admin.site.urls),

    # 2. API uchun manzillar (agar mavjud bo'lsa)
    # Masalan: path('api/v1/', include('auth_app.api_urls')),

    # 3. Barcha boshqa so'rovlarni auth_app ilovasiga yuborish
    # Bu /login/, /tests/, /dashboard/ kabi barcha manzillarni qamrab oladi
    path('', include('auth_app.urls')),
]

# DEBUG rejimida statik fayllarni "serve" qilish uchun
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)