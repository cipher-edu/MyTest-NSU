# auth_app/api_views.py

# --- Django va Rest Framework importlari ---
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView

# --- Mahalliy (Local) importlar ---
from .models import Test, SurveyResponse, Student, StudentAnswer
from .serializers import (
    TestListSerializer, TestTakingDataSerializer, TestResultSerializer, 
    StudentAnswerSubmitSerializer, AdminTestDetailSerializer, AdminSurveyResponseSerializer
)
from .services.hemis_api_service import HemisAPIClient, APIClientException
from .utils import *


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Standart JWT token olishga qo'shimcha ravishda, HEMIS API'ga login qilib,
    talaba ma'lumotlarini sinxronlaydigan maxsus view.
    """
    def post(self, request, *args, **kwargs):
        # Bu qism hozircha to'liq ishlatilmayapti, lekin kelajakda
        # to'g'ridan-to'g'ri API orqali token olish uchun kerak bo'lishi mumkin.
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
            
            # Bu yerdan standart simple-jwt token generatsiya qilish logikasi qo'shilishi kerak.
            # Hozircha bu sozlanmagan.
            return Response({"error": "API token logikasi hali to'liq sozlanmagan."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        except APIClientException:
            return Response({"error": "Login yoki parol xato."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({"error": f"Tizimda kutilmagan xatolik: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from .utils import get_client_ip

# ===================================================================
# --- TALABALAR UCHUN API ENDPOINT'LARI ---
# ===================================================================

class TestListViewAPI(generics.ListAPIView): # NOM O'ZGARTIRILDI
    """Talabaga ruxsat etilgan va aktiv bo'lgan testlar ro'yxatini qaytaradi (API)."""
    serializer_class = TestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        student = self.request.user.student
        now = timezone.now()
        return Test.objects.filter(
            Q(status=Test.Status.ACTIVE),
            Q(start_time__isnull=True) | Q(start_time__lte=now),
            Q(end_time__isnull=True) | Q(end_time__gte=now)
        ).filter(
            Q(faculties__isnull=True) | Q(faculties=student.faculty_id_api),
            Q(specialties__isnull=True) | Q(specialties=student.specialty_id_api),
            Q(groups__isnull=True) | Q(groups=student.group_id_api),
            Q(levels__isnull=True) | Q(levels=student.level_code)
        ).exclude(
            allow_once=True, responses__student=student, responses__is_completed=True
        ).distinct()


class TestDetailViewAPI(generics.RetrieveAPIView):
    serializer_class = TestTakingDataSerializer
    permission_classes = [IsAuthenticated]
    queryset = Test.objects.filter(status=Test.Status.ACTIVE)

    def retrieve(self, request, *args, **kwargs):
        test = self.get_object()
        student = request.user.student

        # IP manzil tekshiruvi
        client_ip = get_client_ip(request)
        if not is_ip_allowed(client_ip, test.allowed_ips):
            raise PermissionDenied(
                f"Ruxsat yo'q: IP manzilingiz ({client_ip}) ruxsat etilgan IP ro'yxatiga mos kelmaydi."
            )

        # Test vaqtini tekshirish
        if not test.is_active:
            raise PermissionDenied(
                "Bu testga faqat belgilangan vaqtda kirish ruxsat etiladi."
            )

        # Talabaning fakultet, guruh va yo'nalishiga mosligini tekshirish
        if test.faculties.exists() and not test.faculties.filter(id=student.faculty_id_api).exists():
            raise PermissionDenied("Bu test sizning fakultetingiz uchun emas.")
        if test.groups.exists() and not test.groups.filter(id=student.group_id_api).exists():
            raise PermissionDenied("Bu test sizning guruhingiz uchun emas.")
        if test.specialties.exists() and not test.specialties.filter(id=student.specialty_id_api).exists():
            raise PermissionDenied("Bu test sizning yo'nalishingiz uchun emas.")

        # Aks holda, test ma'lumotini qaytarish
        serializer = self.get_serializer(test)
        return Response(serializer.data)

class TestSubmitViewAPI(APIView): # NOM O'ZGARTIRILDI
    """Test javoblarini qabul qiladi va baholaydi (API)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, format=None):
        response_obj = get_object_or_404(SurveyResponse, pk=pk, student=request.user.student, is_completed=False)
        serializer = StudentAnswerSubmitSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Определение, является ли это финальной отправкой
        is_final_submit = request.query_params.get('final_submit', 'false').lower() == 'true'

        with transaction.atomic():
            response_obj.student_answers.all().delete()
            answers = [StudentAnswer(response=response_obj, **item) for item in serializer.validated_data]
            StudentAnswer.objects.bulk_create(answers)

            # Отмечаем тест как завершенный только если это финальная отправка
            if is_final_submit:
                response_obj.is_completed = True
                response_obj.end_time = timezone.now()
                response_obj.calculate_score()

        if is_final_submit:
            return Response(TestResultSerializer(response_obj).data, status=status.HTTP_200_OK)
        else:
            # Если это просто сохранение, возвращаем статус без результатов
            return Response({"status": "saved", "message": "Ответы сохранены, но тест не завершен"}, status=status.HTTP_200_OK)

class TestResultListViewAPI(generics.ListAPIView): # NOM O'ZGARTIRILDI
    """Talabaning barcha yakunlangan test natijalari (arxiv) (API)."""
    serializer_class = TestResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SurveyResponse.objects.filter(
            student=self.request.user.student, 
            is_completed=True
        ).select_related('test').order_by('-end_time')


# ===================================================================
# --- ADMINLAR UCHUN API ENDPOINT'LARI ---
# ===================================================================

class AdminTestViewSet(viewsets.ModelViewSet):
    """Admin uchun testlarni boshqarish (CRUD)."""
    queryset = Test.objects.all().order_by('-created_at')
    serializer_class = AdminTestDetailSerializer
    permission_classes = [IsAdminUser]


class AdminResultsViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin uchun barcha test natijalarini filtrlash va ko'rish."""
    serializer_class = AdminSurveyResponseSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = SurveyResponse.objects.filter(is_completed=True).select_related(
            'student', 'test'
        ).prefetch_related(
            'student_answers__question__answers',
            'student_answers__chosen_answer'
        ).order_by('-end_time')
        
        # Kengaytirilgan filtrlash imkoniyatlari
        test_id = self.request.query_params.get('test_id')
        faculty_id = self.request.query_params.get('faculty_id')
        group_id = self.request.query_params.get('group_id')
        
        if test_id:
            queryset = queryset.filter(test_id=test_id)
        if faculty_id:
            queryset = queryset.filter(student__faculty_id_api=faculty_id)
        if group_id:
            queryset = queryset.filter(student__group_id_api=group_id)
            
        return queryset

    @action(detail=False, methods=['post'])
    def auto_complete_expired(self, request):
        """Vaqti tugagan testlarni avtomatik yakunlash"""
        from .utils import auto_complete_expired_tests

        completed_count = auto_complete_expired_tests()
        return Response({
            'status': 'success',
            'message': f'Vaqti tugagan {completed_count} ta test natijasi muvaffaqiyatli yakunlandi',
            'completed_count': completed_count
        })