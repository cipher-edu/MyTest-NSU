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
from django.core.exceptions import ValidationError
from django.db.models import Sum, F

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

def test_source_file_path(instance, filename):
    """Yuklanadigan test fayllari uchun unikal yo'l yaratadi."""
    ext = filename.split('.')[-1]
    new_filename = f"{uuid4()}.{ext}"
    return os.path.join('test_source_files', new_filename)

class Faculty(models.Model):
    """HEMIS API'dan olingan fakultetlar uchun ma'lumotnoma."""
    id = models.IntegerField(primary_key=True, verbose_name="Fakultet ID (API)")
    name = models.CharField(max_length=255, verbose_name="Fakultet nomi")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Fakultet (ma'lumotnoma)"
        verbose_name_plural = "Fakultetlar (ma'lumotnoma)"
        ordering = ['name']

class Specialty(models.Model):
    """HEMIS API'dan olingan yo'nalishlar uchun ma'lumotnoma."""
    id = models.CharField(max_length=100, primary_key=True, verbose_name="Mutaxassislik ID (API)")
    name = models.CharField(max_length=255, verbose_name="Mutaxassislik nomi")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Yo'nalish (ma'lumotnoma)"
        verbose_name_plural = "Yo'nalishlar (ma'lumotnoma)"
        ordering = ['name']
        
class Group(models.Model):
    """HEMIS API'dan olingan guruhlar uchun ma'lumotnoma."""
    id = models.IntegerField(primary_key=True, verbose_name="Guruh ID (API)")
    name = models.CharField(max_length=100, verbose_name="Guruh nomi")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Guruh (ma'lumotnoma)"
        verbose_name_plural = "Guruhlar (ma'lumotnoma)"
        ordering = ['name']

class Test(models.Model):
    """Testlar va ularning sozlamalari uchun asosiy model."""
    class Status(models.TextChoices):
        DRAFT = 'draft', "Qoralama"
        PROCESSING = 'processing', "Fayl qayta ishlanmoqda"
        ACTIVE = 'active', "Aktiv"
        COMPLETED = 'completed', "Yakunlangan"
        ARCHIVED = 'archived', "Arxivlangan"

    title = models.CharField(
        max_length=255, 
        verbose_name="Test nomi",
        help_text="Talabalarga ko'rinadigan test sarlavhasi."
    )
    description = models.TextField(
        blank=True, null=True, 
        verbose_name="Test tavsifi",
        help_text="Test haqida qo'shimcha ma'lumot (ixtiyoriy)."
    )
    time_limit = models.PositiveIntegerField(
        default=30, 
        verbose_name="Vaqt cheklovi (daqiqa)",
        help_text="Testni ishlash uchun ajratilgan vaqt. 0 - cheklanmagan."
    )
    start_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Boshlanish vaqti",
        help_text="Test shu vaqtdan boshlab talabalarga ko'rinadi."
    )
    end_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Tugash vaqti",
        help_text="Test shu vaqtdan keyin yopiladi."
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Test yaratuvchisi",
        help_text="Testni yaratgan o'qituvchi yoki ma'mur.",
        related_name="created_tests"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Test holati"
    )
    allowed_ips = models.JSONField(
        default=list, blank=True,
        verbose_name="Ruxsat etilgan IP manzillar",
        help_text="Testni faqat shu IP manzillardan topshirish mumkin. Bo'sh qoldirilsa - cheklov yo'q."
    )
    faculties = models.ManyToManyField(
        Faculty, blank=True,
        verbose_name="Ruxsat etilgan fakultetlar",
        help_text="Test faqat tanlangan fakultet talabalari uchun ochiq bo'ladi."
    )
    specialties = models.ManyToManyField(
        Specialty, blank=True,
        verbose_name="Ruxsat etilgan yo'nalishlar",
        help_text="Test faqat tanlangan yo'nalish talabalari uchun ochiq bo'ladi."
    )
    groups = models.ManyToManyField(
        Group, blank=True,
        verbose_name="Ruxsat etilgan guruhlar",
        help_text="Test faqat tanlangan guruh talabalari uchun ochiq bo'ladi."
    )
    randomize_questions = models.BooleanField(
        default=True,
        verbose_name="Savollarni aralashtirish",
        help_text="Belgilansa, har bir talabaga savollar tasodifiy tartibda ko'rsatiladi."
    )
    allow_once = models.BooleanField(
        default=True,
        verbose_name="Faqat bir marta topshirish",
        help_text="Belgilansa, talaba testni faqat bir marta yecha oladi."
    )
    source_file = models.FileField(
        upload_to=test_source_file_path,
        blank=True, null=True,
        verbose_name="Test manba fayli (.txt)",
        help_text="Savollar yuklangan original .txt fayli."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    def __str__(self):
        return self.title

    @property
    def max_score(self):
        """Barcha savollar ballari yig'indisini hisoblaydi."""
        return self.questions.aggregate(total=Sum('points'))['total'] or 0
    
    @property
    def is_active(self):
        """Test ayni damda topshirish uchun aktiv yoki yo'qligini tekshiradi."""
        now = timezone.now()
        start_ok = self.start_time is None or self.start_time <= now
        end_ok = self.end_time is None or self.end_time >= now
        return self.status == self.Status.ACTIVE and start_ok and end_ok

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'start_time', 'end_time']),
            models.Index(fields=['creator']),
        ]
        unique_together = [['title', 'creator']]

class Question(models.Model):
    """Test savollari uchun model."""
    class QuestionType(models.TextChoices):
        SINGLE_CHOICE = 'single', "Bitta to'g'ri javob"
        # Kelajakda qo'shilishi mumkin
        # MULTIPLE_CHOICE = 'multiple', "Bir nechta to'g'ri javob"

    test = models.ForeignKey(
        Test, 
        on_delete=models.CASCADE, 
        related_name='questions', 
        verbose_name="Test"
    )
    text = models.TextField(verbose_name="Savol matni")
    question_type = models.CharField(
        max_length=10,
        choices=QuestionType.choices,
        default=QuestionType.SINGLE_CHOICE,
        verbose_name="Savol turi"
    )
    points = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Savol uchun ball",
        help_text="Ushbu savolga to'g'ri javob uchun beriladigan ball."
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Tartib raqami",
        help_text="Savollarni saralash uchun (agar aralashtirish o'chirilgan bo'lsa)."
    )

    def __str__(self):
        return self.text[:80] + '...' if len(self.text) > 80 else self.text
    
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['order', 'id']
        # Bir testda bir xil matnli savol bo'lishini cheklash
        unique_together = [['test', 'text']]

class Answer(models.Model):
    """Savol uchun javob variantlari."""
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='answers', 
        verbose_name="Savol"
    )
    text = models.CharField(max_length=1000, verbose_name="Javob matni")
    is_correct = models.BooleanField(
        default=False, 
        verbose_name="To'g'ri javob",
        help_text="Ushbu javob to'g'riligini belgilang."
    )

    def __str__(self):
        return self.text

    def clean(self):
        # Bitta to'g'ri javobli savollar uchun validatsiya
        if self.question.question_type == Question.QuestionType.SINGLE_CHOICE and self.is_correct:
            if self.question.answers.filter(is_correct=True).exclude(pk=self.pk).exists():
                raise ValidationError(
                    "Bu savol uchun allaqachon to'g'ri javob belgilangan. "
                    "Savol turi 'Bitta to'g'ri javob' bo'lgani uchun faqat bitta variant to'g'ri bo'lishi mumkin."
                )

    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"
        ordering = ['id'] # Yoki '?' orqali tasodifiy saralash uchun

class SurveyResponse(models.Model):
    """Talabaning test topshirish holati (urinishi)."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='test_responses',
        verbose_name="Talaba"
    )
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="Test"
    )
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqti")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Tugagan vaqti")
    score = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.0,
        verbose_name="To'plangan ball"
    )
    is_completed = models.BooleanField(default=False, verbose_name="Yakunlanganmi?")
    
    def calculate_score(self):
        """Talabaning javoblariga asosan yakuniy ballni hisoblaydi."""
        total_score = self.student_answers.filter(
            chosen_answer__is_correct=True
        ).aggregate(
            total_score=Sum('question__points')
        )['total_score']
        self.score = total_score or 0.0
        self.save(update_fields=['score'])
        return self.score
    
    def __str__(self):
        return f"{self.student} - {self.test.title}"
        
    class Meta:
        verbose_name = "Test Natijasi"
        verbose_name_plural = "Test Natijalari"
        # Agar allow_once=True bo'lsa, bu cheklov baza darajasida ta'minlanadi
        unique_together = [['student', 'test']]
        ordering = ['-start_time']

class StudentAnswer(models.Model):
    """Talabaning har bir savolga bergan javobi."""
    response = models.ForeignKey(
        SurveyResponse,
        on_delete=models.CASCADE,
        related_name='student_answers',
        verbose_name="Test urinishi"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='student_answers'
    )
    chosen_answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        null=True, blank=True, # Talaba javob bermasligi mumkin
        related_name='student_selections'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Javob: {self.chosen_answer} - Savol: {self.question}"
        
    class Meta:
        verbose_name = "Talaba javobi"
        verbose_name_plural = "Talaba javoblari"
        unique_together = [['response', 'question']]