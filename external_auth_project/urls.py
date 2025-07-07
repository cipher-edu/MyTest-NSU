# external_auth_project/urls.py

from django.contrib import admin # <<< ENG MUHIM TUZATISH
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# auth_app ilovasidan api_urlpatterns'ni import qilish
from auth_app.urls import api_urlpatterns

urlpatterns = [
    # Admin paneli uchun to'g'ri manzil
    path('admin/', admin.site.urls),

    # API manzillarini 'api' namespace'i bilan qo'shish
    path('api/v1/', include((api_urlpatterns, 'api_app'), namespace='api')),

    # Veb-sahifalarini 'auth_app' namespace'i bilan qo'shish
    path('', include('auth_app.urls', namespace='auth_app')),
]

# DEBUG rejimi uchun statik fayllar sozlamalari
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)