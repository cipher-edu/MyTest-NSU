# auth_app/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User # O'qituvchi/Admin uchun
import os
from uuid import uuid4
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

# --- Mavjud Student modeli (o'zgarishsiz qoldiriladi) ---
class Student(models.Model):
    username = models.CharField(
        max_length=150, unique=True,
        verbose_name="Foydalanuvchi nomi (login)",
        help_text="Tizimga kirish uchun foydalaniladigan login (Talaba ID raqami)"
    )
    student_id_number = models.CharField(max_length=50, unique=True, null=True, blank=True,
                                         verbose_name="Talaba ID raqami (API)",
                                         help_text="API dan olingan talabaning ID raqami")
    api_user_hash = models.CharField(max_length=255, unique=True, null=True, blank=True,
                                     verbose_name="API foydalanuvchi hash",
                                     help_text="API dagi foydalanuvchi uchun unikal SHA256 hash")
    first_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Familiyasi") # API dagi 'second_name'
    patronymic = models.CharField(max_length=100, blank=True, null=True, verbose_name="Otasining ismi") # API dagi 'third_name'
    full_name_api = models.CharField(max_length=255, blank=True, null=True, verbose_name="To'liq F.I.Sh. (API)")
    short_name_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="Qisqa F.I.Sh. (API)")

    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Talabning surati (URL)")
    birth_date_timestamp = models.BigIntegerField(null=True, blank=True, verbose_name="Tug'ilgan sana (timestamp)")
    passport_pin = models.CharField(max_length=50, blank=True, null=True, verbose_name="Pasport PIN")
    passport_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Pasport raqami")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="Telefon raqami")

    gender_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Jinsi kodi")
    gender_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Jinsi")

    university_name_api = models.CharField(max_length=255, blank=True, null=True, verbose_name="Universitet nomi (API)")

    # Specialty (Mutaxassislik)
    specialty_id_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mutaxassislik ID (API)")
    specialty_code_api = models.CharField(max_length=50, blank=True, null=True, verbose_name="Mutaxassislik kodi (API)")
    specialty_name_api = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mutaxassislik nomi (API)")

    # Student Status
    student_status_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Talaba status kodi")
    student_status_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Talaba statusi")

    # Education Form (Ta'lim shakli)
    education_form_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Ta'lim shakli kodi")
    education_form_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ta'lim shakli")

    # Education Type (Ta'lim turi)
    education_type_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Ta'lim turi kodi")
    education_type_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ta'lim turi")

    # Payment Form (To'lov shakli)
    payment_form_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="To'lov shakli kodi")
    payment_form_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="To'lov shakli")

    # Group
    group_id_api = models.IntegerField(null=True, blank=True, verbose_name="Guruh ID (API)")
    group_name_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="Guruh nomi (API)")
    group_education_lang_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Guruh ta'lim tili kodi")
    group_education_lang_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Guruh ta'lim tili")

    # Faculty
    faculty_id_api = models.IntegerField(null=True, blank=True, verbose_name="Fakultet ID (API)")
    faculty_name_api = models.CharField(max_length=255, blank=True, null=True, verbose_name="Fakultet nomi (API)")
    faculty_code_api = models.CharField(max_length=50, blank=True, null=True, verbose_name="Fakultet kodi (API)")

    # Education Language (Asosiy ta'lim tili, guruhnikidan farqli bo'lishi mumkin)
    education_lang_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Ta'lim tili kodi")
    education_lang_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ta'lim tili")

    # Level (Kurs)
    level_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Kurs kodi") # API dagi 'level.code'
    level_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Kurs nomi") # API dagi 'level.name' (kurs nomi)

    # Semester
    semester_id_api = models.IntegerField(null=True, blank=True, verbose_name="Semestr ID (API)")
    semester_code_api = models.CharField(max_length=10, blank=True, null=True, verbose_name="Semestr kodi (API)")
    semester_name_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="Semestr nomi (API)")
    semester_is_current = models.BooleanField(null=True, blank=True, verbose_name="Joriy semestr")
    semester_education_year_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Semestr o'quv yili kodi")
    semester_education_year_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Semestr o'quv yili nomi")
    semester_education_year_is_current = models.BooleanField(null=True, blank=True, verbose_name="Joriy o'quv yili (semestr)")

    avg_gpa = models.CharField(max_length=10, blank=True, null=True, verbose_name="O'rtacha ball (GPA)") # String sifatida, chunki '3.50'
    password_is_valid_api = models.BooleanField(null=True, blank=True, verbose_name="Parol to'g'riligi (API)")

    address_api = models.TextField(blank=True, null=True, verbose_name="Manzil (API)")

    # Country
    country_code_api = models.CharField(max_length=10, blank=True, null=True, verbose_name="Davlat kodi (API)")
    country_name_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="Davlat nomi (API)")

    # Province (Viloyat)
    province_code_api = models.CharField(max_length=20, blank=True, null=True, verbose_name="Viloyat kodi (API)")
    province_name_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="Viloyat nomi (API)")

    # District (Tuman)
    district_code_api = models.CharField(max_length=20, blank=True, null=True, verbose_name="Tuman kodi (API)")
    district_name_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tuman nomi (API)")

    # Social Category
    social_category_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Ijtimoiy toifa kodi")
    social_category_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ijtimoiy toifa nomi")

    # Accommodation (Turar joyi)
    accommodation_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Turar joy kodi")
    accommodation_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Turar joy nomi")

    validate_url_api = models.URLField(max_length=500, blank=True, null=True, verbose_name="Validatsiya havolasi (API)")

    # Tizim uchun ma'lumotlar
    last_login_api = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi kirish (API)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    def __str__(self):
        return self.full_name_api or f"{self.last_name or ''} {self.first_name or ''}".strip() or self.username

    class Meta:
        verbose_name = "Talaba (API)"
        verbose_name_plural = "Talabalar (API)"
        ordering = ['-updated_at', 'last_name', 'first_name']

    @property
    def get_birth_date_display(self):
        if self.birth_date_timestamp:
            try:
                dt_object = timezone.datetime.fromtimestamp(self.birth_date_timestamp, tz=timezone.get_current_timezone())
                return dt_object.strftime('%d-%m-%Y')
            except (ValueError, TypeError, OSError): # Potensial xatoliklarni ushlash
                return "Noma'lum sana (xato)"
        return None

# --- Testlar uchun yangi modellar ---

class Test(models.Model):
    """Test haqidagi umumiy ma'lumotlarni saqlaydi."""
    title = models.CharField(max_length=255, verbose_name="Test sarlavhasi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    
    creator = models.ForeignKey(
        User,  # Testlarni adminlar yoki o'qituvchilar (standart User) yaratadi
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Yaratuvchi (o'qituvchi/admin)"
    )
    
    time_limit_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name="Vaqt chegarasi (daqiqa)",
        help_text="Testni ishlash uchun ajratilgan umumiy vaqt. 0 - cheklanmagan."
    )
    
    pass_percentage = models.PositiveSmallIntegerField(
        default=55,
        verbose_name="O'tish bali (foizda)",
        help_text="Testdan o'tish uchun to'plash kerak bo'lgan minimal foiz."
    )
    
    is_active = models.BooleanField(
        default=False,
        verbose_name="Aktiv",
        help_text="Talabalar uchun ko'rinadigan qilib belgilash."
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        ordering = ['-created_at']


class Question(models.Model):
    """Test ichidagi har bir savolni ifodalaydi."""
    class QuestionType(models.TextChoices):
        SINGLE = 'single_choice', "Bitta to'g'ri javob"
        MULTIPLE = 'multiple_choice', "Bir nechta to'g'ri javob"
        OPEN = 'open_text', "Ochiq matnli javob"

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions', verbose_name="Test")
    text = models.TextField(verbose_name="Savol matni")
    
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.SINGLE,
        verbose_name="Savol turi"
    )
    
    image = models.ImageField(upload_to='question_images/', blank=True, null=True, verbose_name="Rasm")
    
    points = models.PositiveSmallIntegerField(default=1, verbose_name="Ball", help_text="Ushbu savol uchun beriladigan ball.")
    
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    def __str__(self):
        return self.text[:80]

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['order', 'id']


class Answer(models.Model):
    """Har bir savol uchun javob variantlarini saqlaydi."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', verbose_name="Savol")
    text = models.CharField(max_length=500, verbose_name="Javob matni")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'riligi")

    def __str__(self):
        return f"{self.question.text[:30]}... -> {self.text[:30]}..."

    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"


class TestAttempt(models.Model):
    """Talabaning bitta testga bo'lgan urinishini to'liq saqlaydi."""
    class AttemptStatus(models.TextChoices):
        IN_PROGRESS = 'in_progress', "Jarayonda"
        COMPLETED = 'completed', "Tugatilgan"
        
    student = models.ForeignKey(
        Student, # To'g'ri modelga bog'landi!
        on_delete=models.CASCADE,
        related_name='test_attempts',
        verbose_name="Talaba"
    )
    test = models.ForeignKey(Test, on_delete=models.PROTECT, related_name='attempts', verbose_name="Test")
    
    status = models.CharField(max_length=20, choices=AttemptStatus.choices, default=AttemptStatus.IN_PROGRESS, verbose_name="Holati")
    
    score = models.FloatField(default=0, verbose_name="To'plangan ball")
    percentage = models.FloatField(default=0, verbose_name="Natija (foizda)")
    passed = models.BooleanField(default=False, verbose_name="O'tganligi")
    
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqti")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Tugatilgan vaqti")

    def __str__(self):
        return f"{self.student} - {self.test.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
    
    class Meta:
        verbose_name = "Test Urinishi"
        verbose_name_plural = "Test Urinishlari"
        ordering = ['-start_time']


class StudentAnswer(models.Model):
    """Talabaning bitta savolga bergan javobini saqlaydi (bitta urinish doirasida)."""
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='student_answers', verbose_name="Urinish")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Savol")
    
    # "Bir nechta to'g'ri javob"li savollar uchun ManyToManyField qulay
    selected_answers = models.ManyToManyField(Answer, blank=True, verbose_name="Tanlangan javob(lar)")
    
    # Ochiq savollar uchun
    open_answer_text = models.TextField(blank=True, null=True, verbose_name="Ochiq javob matni")
    
    is_correct = models.BooleanField(default=False, verbose_name="To'g'riligi")
    points_earned = models.PositiveSmallIntegerField(default=0, verbose_name="Olingan ball")

    def __str__(self):
        return f"Javob: {self.attempt.student} | Savol: {self.question.text[:50]}"
        
    class Meta:
        verbose_name = "Talaba javobi"
        verbose_name_plural = "Talabalar javoblari"
        unique_together = ('attempt', 'question') # Bitta urinishda bir savolga faqat bir marta javob beriladi