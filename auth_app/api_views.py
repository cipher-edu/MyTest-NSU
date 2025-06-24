from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import *
from .serializers import *
from .permissions import *
from .services.hemis_api_service import HemisAPIClient, APIClientException
from .utils import map_api_data_to_student_model_defaults

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({"error": "Username va password kiritilishi shart."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            api_client = HemisAPIClient()
            api_token, _ = api_client.login(username, password)
            student_info_from_api = api_client.get_account_me(api_token_override=api_token)
            
            with transaction.atomic():
                student_defaults = map_api_data_to_student_model_defaults(student_info_from_api, username)
                student, _ = Student.objects.update_or_create(username=username, defaults=student_defaults)
            
            return Response({"error": "API token logikasi hali to'liq sozlanmagan."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        except APIClientException:
            return Response({"error": "Login yoki parol xato."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({"error": f"Tizimda kutilmagan xatolik: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


