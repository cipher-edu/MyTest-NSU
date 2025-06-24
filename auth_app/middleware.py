# auth_app/middleware.py
from django.utils.deprecation import MiddlewareMixin
from .models import Student

class CurrentStudentMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                request.current_student = request.user.student
            except Student.DoesNotExist:
                request.current_student = None

# settings.py
MIDDLEWARE = [
    # Other middleware...
    'auth_app.middleware.CurrentStudentMiddleware',
]