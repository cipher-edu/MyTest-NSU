from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import transaction
from django.db.models import Q
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


# auth_app/api_views.py

from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from .models import *
from .serializers import *
from .permissions import *
from .services.hemis_api_service import HemisAPIClient, APIClientException
from .utils import map_api_data_to_student_model_defaults



class TestListView(generics.ListAPIView):
    """Talabaga ruxsat etilgan aktiv testlar ro'yxatini qaytaradi."""
    serializer_class = TestListSerializer
    permission_classes = [IsAuthenticated] # Yoki o'zimizning custom permission

    def get_queryset(self):
        student = self.request.user.student # Middleware orqali
        cache_key = f'student_{student.id}_allowed_tests'
        cached_queryset = cache.get(cache_key)

        if cached_queryset is not None:
            return cached_queryset

        now = timezone.now()
        
        # Talabaning fakulteti, yo'nalishi va guruhiga mos testlarni filtrlash
        # Agar test uchun ruxsatlar bo'sh bo'lsa, u hammaga ochiq hisoblanadi.
        queryset = Test.objects.filter(
            Q(status=Test.Status.ACTIVE),
            Q(start_time__isnull=True) | Q(start_time__lte=now),
            Q(end_time__isnull=True) | Q(end_time__gte=now)
        ).filter(
            Q(faculties__isnull=True) | Q(faculties__id=student.faculty_id_api),
            Q(specialties__isnull=True) | Q(specialties__id=student.specialty_id_api),
            Q(groups__isnull=True) | Q(groups__id=student.group_id_api),
            # (YANGI)
            Q(levels__isnull=True) | Q(levels__code=student.level_code)
        ).exclude(
            Q(allow_once=True) & Q(responses__student=student, responses__is_completed=True)
        ).distinct().prefetch_related('questions')
        
        cache.set(cache_key, list(queryset), timeout=60 * 15) # 15 daqiqaga keshlash
        return queryset

class TestDetailView(generics.RetrieveAPIView):
    """
    Testni boshlash uchun uning to'liq ma'lumotlarini (savollari bilan) qaytaradi.
    Bu view chaqirilganda talaba uchun test urinishi (SurveyResponse) yaratiladi.
    """
    serializer_class = TestDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
         # TestList'dagi logikani qayta ishlatib, faqat ruxsat etilgan testlarni olamiz
        student = self.request.user.student
        return Test.objects.filter(
            Q(status=Test.Status.ACTIVE) &
            (Q(faculties__isnull=True) | Q(faculties__id=student.faculty_id_api)) &
            (Q(specialties__isnull=True) | Q(specialties__id=student.specialty_id_api)) &
            (Q(groups__isnull=True) | Q(groups__id=student.group_id_api)) &
            # (YANGI)
            (Q(levels__isnull=True) | Q(levels__code=student.level_code))
        ).distinct()


    def get_object(self):
        obj = super().get_object()
        student = self.request.user.student
        
        # IP manzilni tekshirish
        if obj.allowed_ips:
            # X-Forwarded-For kabi headerlarni ham hisobga olish kerak
            x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0]
            else:
                client_ip = self.request.META.get('REMOTE_ADDR')
            
            if client_ip not in obj.allowed_ips:
                raise PermissionDenied("Testni faqat ruxsat etilgan IP manzillardan topshirish mumkin.")

        # `allow_once` logikasi: agar yakunlangan urinish bo'lsa, xatolik beradi
        if obj.allow_once and SurveyResponse.objects.filter(test=obj, student=student, is_completed=True).exists():
            raise PermissionDenied("Siz bu testni allaqachon topshirib bo'lgansiz.")
            
        return obj

    def retrieve(self, request, *args, **kwargs):
        test = self.get_object()
        student = request.user.student
        
        # Test urinishini yaratish yoki mavjudini olish
        response_obj, created = SurveyResponse.objects.get_or_create(
            student=student, 
            test=test,
            is_completed=False # Faqat tugallanmagan urinishni olish
        )
        
        if created and test.time_limit > 0:
            # `end_time` faqat yangi urinish uchun o'rnatiladi
            response_obj.end_time = timezone.now() + timezone.timedelta(minutes=test.time_limit)
            response_obj.save(update_fields=['end_time'])
            
        # Agar vaqt tugagan bo'lsa
        if response_obj.end_time and timezone.now() > response_obj.end_time:
             if not response_obj.is_completed:
                 response_obj.is_completed = True
                 response_obj.calculate_score() # Vaqt tugaguncha berilgan javoblarni hisoblash
                 response_obj.save()
             return Response({"detail": "Bu test uchun ajratilgan vaqt tugagan."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(test)
        data = serializer.data
        data['response_id'] = response_obj.id
        # Qolgan vaqtni hisoblash
        time_left = (response_obj.end_time - timezone.now()).total_seconds() if response_obj.end_time else None
        data['time_left_seconds'] = max(0, time_left) if time_left is not None else None
        
        return Response(data)

class TestSubmitView(APIView):
    """Test javoblarini qabul qilish, baholash va natijani saqlash."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, format=None):
        student = request.user.student
        response_obj = get_object_or_404(SurveyResponse, pk=pk, student=student, is_completed=False)

        serializer = StudentAnswerSubmitSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Vaqt tugaganini tekshirish
            if response_obj.end_time and timezone.now() > response_obj.end_time:
                response_obj.is_completed = True
                response_obj.calculate_score()
                response_obj.save()
                return Response({"detail": "Vaqt tugadi. Javoblaringiz saqlandi."}, status=status.HTTP_403_FORBIDDEN)

            answers_data = serializer.validated_data
            
            # Eski javoblarni o'chirish va yangilarini bitta tranzaksiyada qo'shish
            StudentAnswer.objects.filter(response=response_obj).delete()

            student_answers_to_create = []
            for item in answers_data:
                # Javob urinishga tegishli testdagi savolga berilganini tekshirish
                if item['question_id'].test != response_obj.test:
                    continue
                student_answers_to_create.append(
                    StudentAnswer(
                        response=response_obj,
                        question=item['question_id'],
                        chosen_answer=item['answer_id']
                    )
                )
            
            StudentAnswer.objects.bulk_create(student_answers_to_create, ignore_conflicts=True)

            response_obj.is_completed = True
            response_obj.end_time = timezone.now()
            response_obj.calculate_score() # Yakuniy ballni hisoblash
            # save() allaqachon calculate_score ichida chaqiriladi

        result_serializer = TestResultSerializer(response_obj)
        return Response(result_serializer.data, status=status.HTTP_200_OK)

class TestResultListView(generics.ListAPIView):
    """Talabaning barcha yakunlangan test natijalari (arxiv)."""
    serializer_class = TestResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SurveyResponse.objects.filter(
            student=self.request.user.student, 
            is_completed=True
        ).select_related('test').order_by('-end_time')


# --- Admin uchun API ViewSet'lar ---

class AdminTestViewSet(viewsets.ModelViewSet):
    """Admin uchun testlarni boshqarish (CRUD)."""
    queryset = Test.objects.all().order_by('-created_at')
    serializer_class = TestDetailSerializer # Admin uchun alohida serializator yaratish mumkin
    permission_classes = [IsAdminUser]

class AdminResultsViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin uchun natijalarni filtrlash va ko'rish."""
    serializer_class = AdminTestResultDetailSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = SurveyResponse.objects.filter(is_completed=True).select_related(
            'student', 'test'
        ).prefetch_related(
            'student_answers__question', 'student_answers__chosen_answer'
        )
        
        # Kengaytirilgan filtrlash
        test_id = self.request.query_params.get('test_id')
        faculty_id = self.request.query_params.get('faculty_id')
        specialty_id = self.request.query_params.get('specialty_id')
        group_id = self.request.query_params.get('group_id')
        
        if test_id:
            queryset = queryset.filter(test_id=test_id)
        if faculty_id:
            queryset = queryset.filter(student__faculty_id_api=faculty_id)
        if specialty_id:
            queryset = queryset.filter(student__specialty_id_api=specialty_id)
        if group_id:
            queryset = queryset.filter(student__group_id_api=group_id)
            
        return queryset