# auth_app/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Faqat admin huquqiga ega (is_staff=True) foydalanuvchilarga ruxsat beradi.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff