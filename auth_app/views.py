# auth_app/views.py
import logging
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.core.cache import cache
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .decorators import custom_login_required_with_token_refresh
from .forms import *
from .models import * # Barcha modellarni import qilish
from .services.hemis_api_service import HemisAPIClient, APIClientException
from .utils import *

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.http import Http404, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from .decorators import custom_login_required_with_token_refresh
from .forms import *
from .models import *
from .services.hemis_api_service import HemisAPIClient, APIClientException
from .utils import get_client_ip, is_ip_allowed 
logger = logging.getLogger(__name__)
REQUESTS_VERIFY_SSL = getattr(settings, 'REQUESTS_VERIFY_SSL', True)
API_TOKEN_REFRESH_THRESHOLD_SECONDS = getattr(settings, 'API_TOKEN_REFRESH_THRESHOLD_SECONDS', 5 * 60) # default 5 daqiqa

class AuthenticationFailed(APIClientException):
    pass

class PermissionDeniedAPI(APIClientException):
    pass

# --- Helper Functions ---
def _get_error_log_id():
    return timezone.now().strftime('%Y%m%d%H%M%S%f')

def _handle_api_token_refresh(request):
    refresh_cookie = request.session.get('hemis_refresh_cookie')
    current_token_expiry = request.session.get('api_token_expiry_timestamp')
    log_id_base = _get_error_log_id()

    needs_refresh = not current_token_expiry or \
                    current_token_expiry <= timezone.now().timestamp() + API_TOKEN_REFRESH_THRESHOLD_SECONDS

    if not refresh_cookie or not needs_refresh:
        return True

    # '127.0.0.1' uchun har doim ruxsat berish (test qilish uchun)
    client_ip_str = get_client_ip(request)
    if client_ip_str == '127.0.0.1':
        return True

    logger.info(f"Attempting to refresh API token for session: {request.session.session_key}")
    api_client = HemisAPIClient() # Token bu yerda kerak emas, refresh_auth_token o'zi refresh_cookie ni ishlatadi
    log_id = f"{log_id_base}_REFRESH"

    try:
        new_access_token, new_refresh_cookie_data = api_client.refresh_auth_token(refresh_cookie)
        request.session['api_token'] = new_access_token
        
        # API javobidan 'expires_in' olishga harakat qilamiz
        expires_in = settings.SESSION_COOKIE_AGE # default
        if isinstance(new_refresh_cookie_data, dict) and 'expires_in' in new_refresh_cookie_data:
            try:
                expires_in = int(new_refresh_cookie_data['expires_in'])
            except (ValueError, TypeError):
                logger.warning(f"API dan kelgan 'expires_in' ({new_refresh_cookie_data['expires_in']}) yaroqsiz. Standart qiymat ishlatiladi.")
        
        request.session['api_token_expiry_timestamp'] = timezone.now().timestamp() + expires_in

        # Agar API yangi refresh cookie qaytarsa (string yoki dict ichida)
        new_actual_refresh_cookie = None
        if isinstance(new_refresh_cookie_data, str):
            new_actual_refresh_cookie = new_refresh_cookie_data
        elif isinstance(new_refresh_cookie_data, dict) and new_refresh_cookie_data.get('refresh_token_cookie_value'):
            new_actual_refresh_cookie = new_refresh_cookie_data['refresh_token_cookie_value']
        elif isinstance(new_refresh_cookie_data, dict) and new_refresh_cookie_data.get('refresh_cookie'): # Boshqa nom bilan kelishi mumkin
            new_actual_refresh_cookie = new_refresh_cookie_data['refresh_cookie']


        if new_actual_refresh_cookie:
            request.session['hemis_refresh_cookie'] = new_actual_refresh_cookie
            logger.info(f"Refresh cookie also updated for session: {request.session.session_key}")
        
        logger.info(f"API token successfully refreshed for session: {request.session.session_key}. New expiry: {timezone.datetime.fromtimestamp(request.session['api_token_expiry_timestamp'])}")
        return True
    except APIClientException as e:
        logger.error(f"Error Log ID: {log_id} - Failed to refresh API token: {e.args[0]} (Status: {e.status_code})", 
                     extra={'response_data': e.response_data, 'session_key': request.session.session_key})
        request.session.flush()
        messages.error(request, f"Sessiyangiz muddati tugadi. Iltimos, qayta kiring. (Xatolik ID: {log_id})")
        return False
    except Exception as e:
        logger.critical(f"Error Log ID: {log_id} - Unexpected error during token refresh: {e}", 
                        exc_info=True, extra={'session_key': request.session.session_key})
        request.session.flush()
        messages.error(request, f"Tokenni yangilashda kutilmagan xatolik. Qayta kiring. (Xatolik ID: {log_id})")
        return False

# --- Decorators ---
def custom_login_required_with_token_refresh(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        student_db_id_in_session = request.session.get('student_db_id')
        api_token_in_session = request.session.get('api_token')

        if not api_token_in_session or not student_db_id_in_session:
            messages.warning(request, "Iltimos, davom etish uchun tizimga kiring.")
            login_url_name = settings.LOGIN_URL # Bu odatda URL nomi bo'ladi
            try:
                login_url_path = reverse(login_url_name)
            except Exception:
                login_url_path = f"/{login_url_name}/" # Fallback agar reverse ishlamasa
            
            current_path = request.get_full_path()
            return redirect(f'{login_url_path}?next={current_path}')
        
        try:
            request.current_student = Student.objects.get(pk=student_db_id_in_session)
        except Student.DoesNotExist:
            logger.warning(f"Student ID {student_db_id_in_session} from session not found in DB. Flushing session.")
            request.session.flush()
            messages.error(request, "Sessiya yaroqsiz yoki foydalanuvchi topilmadi. Iltimos, qayta kiring.")
            return redirect(settings.LOGIN_URL) # LOGIN_URL bu yerda ham nom bo'lishi kerak

        if not _handle_api_token_refresh(request):
            # _handle_api_token_refresh xabar berib, sessiyani tozalab, False qaytaradi.
            # Login sahifasiga redirect kerak.
            return redirect(settings.LOGIN_URL)
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# --- Views ---
def login_view(request):
    """Foydalanuvchini HEMIS API orqali autentifikatsiya qiladi va ma'lumotlarini sinxronlaydi."""
    
    # Agar foydalanuvchi allaqachon tizimga kirgan bo'lsa
    if 'api_token' in request.session and 'student_db_id' in request.session:
        if _handle_api_token_refresh(request):
            try:
                # Foydalanuvchi hali ham bazada mavjudligini tekshirish
                Student.objects.get(pk=request.session['student_db_id'])
                next_url = request.session.pop('login_next_url', None) or request.GET.get('next')
                return redirect(next_url or 'auth_app:dashboard')
            except Student.DoesNotExist:
                logger.warning(f"Sessiyadagi foydalanuvchi (ID: {request.session.get('student_db_id')}) bazadan topilmadi. Sessiya tozalanmoqda.")
                request.session.flush()
        else:
            # Tokenni yangilash muvaffaqiyatsiz bo'lsa, login sahifasiga qaytamiz
            return redirect(settings.LOGIN_URL)

    # `next` parametrini sessiyaga saqlash
    if request.method == 'GET' and 'next' in request.GET:
        request.session['login_next_url'] = request.GET.get('next')

    form = LoginForm(request.POST or None)
    log_id_base = _get_error_log_id()

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        api_client = HemisAPIClient()

        try:
            logger.info(f"Foydalanuvchi '{username}' uchun tizimga kirishga urinish.")
            api_token, refresh_data = api_client.login(username, password)
            
            logger.info(f"'{username}' uchun login muvaffaqiyatli, yangi token bilan ma'lumotlar olinmoqda.")
            student_info_from_api = api_client.get_account_me(api_token_override=api_token)

            if not student_info_from_api or not isinstance(student_info_from_api, dict):
                log_id = f"{log_id_base}_NODATA"
                logger.error(f"Xatolik ID: {log_id} - '{username}' uchun API'dan talaba ma'lumotlari kelmadi yoki format noto'g'ri. Javob: {str(student_info_from_api)[:250]}")
                messages.error(request, f"API dan ma'lumot olishda xatolik yuz berdi. (ID: {log_id})")
                return render(request, 'auth_app/login.html', {'form': form})

            with transaction.atomic():
                # 1. API ma'lumotlarini model uchun tayyorlash
                student_defaults = map_api_data_to_student_model_defaults(student_info_from_api, username)
                if not student_defaults:
                    raise ValueError("API ma'lumotlarini modellashtirishda xatolik.")

                # 2. Talaba ma'lumotlarini bazada yaratish yoki yangilash
                student, created = Student.objects.update_or_create(
                    username=username,
                    defaults=student_defaults
                )
                
                # --- ENG MUHIM QO'SHIMCHA ---
                # 3. Ma'lumotnoma jadvallarini (Fakultet, Yo'nalish va h.k.) sinxronlash
                sync_reference_models_from_student(student)
                # -------------------------
            
            # 4. Sessiyani sozlash
            request.session['api_token'] = api_token
            request.session['student_db_id'] = student.id
            request.session['username_display'] = str(student)
            
            expires_in_login = settings.SESSION_COOKIE_AGE
            refresh_cookie_login = None

            if isinstance(refresh_data, str):
                refresh_cookie_login = refresh_data
            elif isinstance(refresh_data, dict):
                if 'expires_in' in refresh_data:
                    try:
                        expires_in_login = int(refresh_data['expires_in'])
                    except (ValueError, TypeError):
                        logger.warning(f"Login API javobidagi 'expires_in' ({refresh_data['expires_in']}) yaroqsiz.")
                
                # Turli nomlar bilan kelishi mumkin bo'lgan refresh cookie'ni qidirish
                refresh_cookie_login = refresh_data.get('refresh_token_cookie_value') or refresh_data.get('refresh_cookie')
            
            request.session['api_token_expiry_timestamp'] = timezone.now().timestamp() + expires_in_login
            
            if refresh_cookie_login:
                request.session['hemis_refresh_cookie'] = refresh_cookie_login
            
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)

            # 5. Muvaffaqiyatli kirish va yo'naltirish
            display_name = student.short_name_api or student.username
            messages.success(request, f"Xush kelibsiz, {display_name}!")
            logger.info(f"Foydalanuvchi '{username}' tizimga kirdi. Sessiya muddati: {request.session.get_expiry_date()}, API token muddati: {timezone.datetime.fromtimestamp(request.session['api_token_expiry_timestamp'])}")
            
            next_url = request.session.pop('login_next_url', None) or request.GET.get('next')
            return redirect(next_url or 'dashboard')

        except APIClientException as e:
            log_id = f"{log_id_base}_APICLI"
            logger.error(
                f"Xatolik ID: {log_id} - Foydalanuvchi: {username}, APIClientException: {e.args[0]}, "
                f"Status: {e.status_code}, API Javob: {str(e.response_data)[:250]}, URL: {e.url}"
            )
            # Foydalanuvchiga tushunarli xabar berish
            if e.status_code in [400, 401, 403]:
                 user_message = "Login yoki parol xato."
            elif e.status_code in [503, 504] or e.status_code is None:
                user_message = "API serveriga ulanishda muammo yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
            else:
                 user_message = "API bilan bog'lanishda noma'lum xatolik."
            messages.error(request, f"{user_message} (ID: {log_id})")
        
        except ValueError as ve:
            log_id = f"{log_id_base}_VALERR"
            logger.error(f"Xatolik ID: {log_id} - Foydalanuvchi: {username}, Ma'lumotlarni qayta ishlashda xatolik: {ve}", exc_info=True)
            messages.error(request, f"Ma'lumotlarni qayta ishlashda xatolik yuz berdi. (ID: {log_id})")

        except Exception as e:
            log_id = f"{log_id_base}_UNEXP"
            logger.critical(f"Xatolik ID: {log_id} - Foydalanuvchi: {username}, login_view'da kutilmagan xatolik: {type(e).__name__} - {e}", exc_info=True)
            messages.error(request, f"Noma'lum tizim xatoligi. Administratorga murojaat qiling. (ID: {log_id})")

    context = {'form': form}
    return render(request, 'auth_app/login.html', context)

def logout_view(request):
    api_token = request.session.get('api_token')
    session_key = request.session.session_key # flush dan oldin olish
    if api_token and hasattr(settings, 'EXTERNAL_API_LOGOUT_ENDPOINT') and settings.EXTERNAL_API_LOGOUT_ENDPOINT:
        try:
            client = HemisAPIClient(api_token=api_token)
            # `logout` metodi HemisAPIClient'da bo'lishi kerak va EXTERNAL_API_LOGOUT_ENDPOINT'ga so'rov yuborishi kerak.
            # Masalan, client.logout_on_api()
            # Agar API logoutni qo'llab-quvvatlamasa, bu qismni olib tashlash kerak.
            # client.logout_on_api() # Bu metod mavjud deb faraz qilamiz
            logger.info(f"API token (if supported by API) might be invalidated for session {session_key}")
        except APIClientException as e:
            logger.warning(f"Failed to invalidate API token on API-side logout for session {session_key}: {e}")
        except Exception:
            logger.warning(f"Unexpected error during API-side logout for session {session_key}", exc_info=True)

    request.session.flush()
    messages.info(request, "Siz tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect(settings.LOGIN_URL)


def home_view(request):
    if 'api_token' in request.session and 'student_db_id' in request.session:
        if _handle_api_token_refresh(request):
            return redirect('auth_app:dashboard')
        else:
            return redirect(settings.LOGIN_URL)
    # Agar LOGIN_URL 'login' bo'lsa, templates/home.html ni render qilish o'rniga
    # to'g'ridan-to'g'ri login sahifasiga yo'naltirish mumkin.
    # return redirect(settings.LOGIN_URL)
    return render(request, 'auth_app/home.html')


@custom_login_required_with_token_refresh 
def dashboard_view(request):
    current_student = getattr(request, 'current_student', None) # Dekorator o'rnatadi

    if not current_student: # Bu holat kamdan-kam yuz berishi kerak
        logger.error(f"FATAL: current_student not found in request for dashboard despite decorator. Session: {request.session.session_key}")
        request.session.flush()
        messages.error(request, "Kritik sessiya xatoligi. Iltimos, qayta kiring.")
        return redirect(settings.LOGIN_URL)
    
    # Dashboardga har kirganda profilni yangilash (agar kerak bo'lsa va interval o'tgan bo'lsa)
    # Bu foydalanuvchi uchun yuklamani oshirishi mumkin. Celery task afzalroq.
    # refresh_interval = timezone.timedelta(minutes=getattr(settings, "DASHBOARD_PROFILE_REFRESH_INTERVAL_MINUTES", 30))
    # last_updated_threshold = timezone.now() - refresh_interval

    # if current_student.updated_at < last_updated_threshold:
    #     logger.info(f"Student {current_student.username} profile data is older than {refresh_interval}. Attempting refresh.")
    #     try:
    #         api_client = HemisAPIClient(api_token=request.session.get('api_token')) # Token sessiyadan olinadi
    #         student_info_from_api = api_client.get_account_me()
    #         if student_info_from_api and isinstance(student_info_from_api, dict):
    #             student_defaults = map_api_data_to_student_model_defaults(student_info_from_api, current_student.username)
    #             if student_defaults:
    #                 update_student_instance_with_defaults(current_student, student_defaults)
    #                 # current_student ni qayta yuklash kerak emas, chunki update_student_instance_with_defaults o'zgartiradi
    #                 messages.info(request, "Profil ma'lumotlaringiz yangilandi.")
    #             else:
    #                 logger.warning(f"Could not map API data for student {current_student.username} during dashboard refresh.")
    #         else:
    #             logger.warning(f"No data or invalid data from API for {current_student.username} during dashboard refresh.")
    #     except APIClientException as e:
    #         messages.warning(request, f"Profilni API dan yangilab bo'lmadi: {e.args[0]}")
    #         logger.error(f"APIClientException during dashboard profile refresh for {current_student.username}: {e}", exc_info=True)
    #     except Exception as e:
    #         logger.error(f"Unexpected error during dashboard profile refresh for {current_student.username}: {e}", exc_info=True)
    #         messages.error(request, "Profilni yangilashda kutilmagan xatolik yuz berdi.")


    context = {
        'student': current_student, # Endi bu yangilangan bo'lishi mumkin
        'username_display': str(current_student),
    }
    return render(request, 'auth_app/dashboard.html', context)

# auth_app/views.py




# auth_app/views.py

# ... boshqa importlar ...
import logging
logger = logging.getLogger(__name__)

# ... boshqa view'lar ...


# auth_app/views.py

@method_decorator(custom_login_required_with_token_refresh, name='dispatch')
class TestListView(ListView):
    model = Test
    template_name = 'auth_app/test_list.html'
    context_object_name = 'tests'
    paginate_by = 10

    def get_queryset(self):
        student = self.request.current_student
        now = timezone.now()
        client_ip = get_client_ip(self.request)

        # Talabaning ma'lumotlari mavjudligini tekshirish
        if not all([student.faculty_id_api, student.specialty_id_api, student.group_id_api, student.level_code]):
            logger.warning(f"Talaba '{student.username}' uchun to'liq ma'lumotlar (fakultet, yo'nalish, guruh, kurs) mavjud emas. Testlar ko'rsatilmaydi.")
            return Test.objects.none() # Bo'sh ro'yxat qaytarish

        # Aktiv va vaqti to'g'ri keladigan testlarni olish
        active_tests = Test.objects.filter(
            status=Test.Status.ACTIVE,
            start_time__lte=now
        ).filter(Q(end_time__isnull=True) | Q(end_time__gte=now))

        # Ruxsatlar bo'yicha filtrlash
        allowed_tests = active_tests.filter(
            Q(faculties=student.faculty_id_api) | Q(faculties__isnull=True),
            Q(specialties=student.specialty_id_api) | Q(specialties__isnull=True),
            Q(groups=student.group_id_api) | Q(groups__isnull=True),
            Q(levels=student.level_code) | Q(levels__isnull=True),
        )

        # Filtrlash natijalarini to'plash
        tests_list = []
        for test in allowed_tests:
            # IP manzil bo'yicha tekshirish
            if is_ip_allowed(client_ip, test.allowed_ips):
                # Test bir marta topshirilgan yoki yo'qligini tekshirish
                if not (test.allow_once and SurveyResponse.objects.filter(
                    test=test, student=student, is_completed=True).exists()):
                    tests_list.append(test.id)

        # ID'lar bo'yicha queryset qaytarish
        final_queryset = Test.objects.filter(id__in=tests_list).order_by('-start_time', '-created_at')
        return final_queryset


# @custom_login_required_with_token_refresh
# def take_test_view(request, test_id):
#     test = get_object_or_404(Test, pk=test_id)
#     student = request.current_student

#     # --- QAT'IY RUXSAT TEKSHIRUVI ---
#     is_allowed = True
#     error_message = ""
#     now = timezone.now()

#     # 1. Status tekshiruvi
#     if test.status != Test.Status.ACTIVE:
#         is_allowed = False
#         error_message = "Bu test hozir aktiv emas."

#     # 2. Vaqt tekshiruvi
#     if is_allowed and not ((test.start_time is None or test.start_time <= now) and (test.end_time is None or test.end_time >= now)):
#         is_allowed = False
#         error_message = "Test vaqti to'g'ri kelmadi."

#     # 3. Fakultet, Yo'nalish, Guruh, Kurs tekshiruvi
#     if is_allowed and test.faculties.exists() and not test.faculties.filter(id=student.faculty_id_api).exists():
#         is_allowed = False
#         error_message = "Sizning fakultetingizga ruxsat yo'q."
    
#     if is_allowed and test.specialties.exists() and not test.specialties.filter(id=student.specialty_id_api).exists():
#         is_allowed = False
#         error_message = "Sizning yo'nalishingizga ruxsat yo'q."

#     if is_allowed and test.groups.exists() and not test.groups.filter(id=student.group_id_api).exists():
#         is_allowed = False
#         error_message = "Sizning guruhingizga ruxsat yo'q."

#     if is_allowed and test.levels.exists() and not test.levels.filter(code=student.level_code).exists():
#         is_allowed = False
#         error_message = "Sizning kursingizga ruxsat yo'q."

#     if not is_allowed:
#         messages.error(request, f"Sizga bu testni topshirishga ruxsat yo'q. Sabab: {error_message}")
#         return redirect('test-list')
    
#     # 4. Yakunlangan testni tekshirish
#     if test.allow_once and SurveyResponse.objects.filter(test=test, student=student, is_completed=True).exists():
#         messages.warning(request, "Siz bu testni allaqachon topshirib bo'lgansiz.")
#         return redirect('test-detail', pk=test.id)

#     # Agar barcha tekshiruvlardan o'tsa, testni boshlash
#     response_obj, created = SurveyResponse.objects.get_or_create(...)
    
#     context = {
#         'test_id': test.id,
#         'test_title': test.title,
#         'response_id': response_obj.id,
#         'api_token': request.session.get('api_token'),
        
#         # --- MUHIM QISM: TO'G'RI MANZIL UZATILMOQDA ---
#         # `api:api-test-detail` bu talaba uchun mo'ljallangan view
#         'api_test_detail_url': reverse('api:api-test-detail', kwargs={'pk': test.id}),
        
#         'api_test_submit_url': reverse('api:api-test-submit', kwargs={'pk': response_obj.id})
#     }
#     return render(request, 'auth_app/take_test.html', context)


# auth_app/views.py

# ... mavjud importlar ...

# @custom_login_required_with_token_refresh
# def take_test_view(request, test_id):
#     """Test topshirish sahifasi. Ma'lumotlarni tayyorlab, shablonga uzatadi."""
#     test = get_object_or_404(Test, pk=test_id)
#     student = request.current_student
#     now = timezone.now()

#     # --- QAT'IY RUXSAT TEKSHIRUVI ---
#     error_message = ""
#     if test.status != Test.Status.ACTIVE:
#         error_message = "Bu test hozir aktiv emas."
#     elif not ((test.start_time is None or test.start_time <= now) and (test.end_time is None or test.end_time >= now)):
#         error_message = "Test vaqti to'g'ri kelmadi."
#     elif test.allowed_ips and get_client_ip(request) not in test.allowed_ips:
#         error_message = f"Sizning IP manzilingizga ({get_client_ip(request)}) bu testni topshirishga ruxsat yo'q."
#     elif test.faculties.exists() and not test.faculties.filter(id=student.faculty_id_api).exists():
#         error_message = "Sizning fakultetingizga ruxsat yo'q."
#     # ... boshqa ruxsat tekshiruvlarini qo'shish mumkin

#     if error_message:
#         messages.error(request, f"Ruxsat yo'q. Sabab: {error_message}")
#         return redirect('auth_app:test-list')

#     if test.allow_once and SurveyResponse.objects.filter(test=test, student=student, is_completed=True).exists():
#         messages.warning(request, "Siz bu testni allaqachon topshirib bo'lgansiz.")
#         return redirect('auth_app:test-detail', pk=test.id)

#     response_obj, created = SurveyResponse.objects.get_or_create(student=student, test=test, is_completed=False)

#     time_left_seconds = None
#     if test.time_limit > 0:
#         if created:
#             response_obj.end_time = now + timezone.timedelta(minutes=test.time_limit)
#             response_obj.save(update_fields=['end_time'])
#         if response_obj.end_time:
#             time_left_seconds = max(0, (response_obj.end_time - now).total_seconds())

#     questions_query = test.questions.prefetch_related('answers')
#     questions = questions_query.order_by('?') if test.randomize_questions else questions_query.order_by('order')

#     context = {
#         'test': test,
#         'questions': questions,
#         'response': response_obj,
#         'time_left_seconds': time_left_seconds,
#     }
#     return render(request, 'auth_app/take_test.html', context)

@custom_login_required_with_token_refresh
def submit_test_view(request, response_id):
    """
    HTML formadan kelgan test javoblarini qabul qiladi va baholaydi.
    """
    if request.method != 'POST':
        return redirect('auth_app:home')

    student = request.current_student
    response_obj = get_object_or_404(SurveyResponse, pk=response_id, student=student, is_completed=False)

    # Vaqt tugaganini tekshirish
    if response_obj.end_time and timezone.now() > response_obj.end_time:
        messages.error(request, "Afsuski, test uchun ajratilgan vaqt tugadi.")
    
    with transaction.atomic():
        # Eski javoblarni tozalash
        response_obj.student_answers.all().delete()
        
        answers_to_create = []
        for key, value in request.POST.items():
            if key.startswith('question_'):
                try:
                    question_id = int(key.split('_')[1])
                    answer_id = int(value)
                    answers_to_create.append(
                        StudentAnswer(
                            response=response_obj,
                            question_id=question_id,
                            chosen_answer_id=answer_id
                        )
                    )
                except (ValueError, IndexError):
                    continue # Noto'g'ri formatdagi ma'lumotni o'tkazib yuborish
        
        if answers_to_create:
            StudentAnswer.objects.bulk_create(answers_to_create)

        # Testni yakunlangan deb belgilash va ballni hisoblash
        response_obj.is_completed = True
        response_obj.end_time = timezone.now()
        response_obj.calculate_score() # Bu metod o'z ichida .save() ni chaqiradi

    messages.success(request, "Test muvaffaqiyatli yakunlandi! Natijangiz saqlandi.")
    return redirect('auth_app:test-result-detail', pk=response_obj.id)


@method_decorator(custom_login_required_with_token_refresh, name='dispatch')
class TestDetailView(DetailView):
    model = Test
    template_name = 'auth_app/test_detail.html'
    context_object_name = 'test'

    def get_queryset(self):
        return Test.objects.filter(status=Test.Status.ACTIVE)

    def get(self, request, *args, **kwargs):
        # Foydalanuvchining IP manzilini olish
        client_ip = get_client_ip(request)
        test = self.get_object()

        # IP xabar tayyorlash
        ip_message = f"Sizning IP manzilingiz: {client_ip}"
        if test.allowed_ips:
            allowed_ips = [ip.strip() for ip in test.allowed_ips.split(',') if ip.strip()]
            ip_message += f"\nBu test uchun IP manzil cheklovlari mavjud."
            if client_ip in allowed_ips or client_ip == '127.0.0.1':
                ip_message += "\nSizning IP manzilingiz ruxsat etilgan!"
            else:
                ip_message += "\nSizning IP manzilingizga ruxsat yo'q!"
        else:
            ip_message += "\nBu test uchun IP manzil cheklovlari mavjud emas."

        ip_message += "\n\nDiqqat: Bu test rejimida ishlamoqda!"
        messages.info(request, ip_message)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        test = self.get_object()
        student = self.request.current_student
        now = timezone.now()

        # IP manzil ma'lumotlarini kontekstga qo'shish
        client_ip = get_client_ip(self.request)
        allowed_ips = []
        if test.allowed_ips:
            allowed_ips = [ip.strip() for ip in test.allowed_ips.split(',') if ip.strip()]

        context['client_ip'] = client_ip
        context['allowed_ips'] = allowed_ips
        context['ip_is_allowed'] = not allowed_ips or client_ip in allowed_ips or client_ip == '127.0.0.1'

        # Mavjud test tekshiruvlar
        result = SurveyResponse.objects.filter(test=test, student=student, is_completed=True).first()
        context['result'] = result
        context['is_already_completed'] = result is not None

        # Testga kirish huquqini tekshirish
        is_allowed_to_take = True
        if not ((test.start_time is None or test.start_time <= now) and (
                test.end_time is None or test.end_time >= now)):
            is_allowed_to_take = False
        elif test.allowed_ips and not context['ip_is_allowed']:
            is_allowed_to_take = False
        elif test.faculties.exists() and not test.faculties.filter(id=student.faculty_id_api).exists():
            is_allowed_to_take = False
        elif test.specialties.exists() and not test.specialties.filter(id=student.specialty_id_api).exists():
            is_allowed_to_take = False
        elif test.groups.exists() and not test.groups.filter(id=student.group_id_api).exists():
            is_allowed_to_take = False
        elif test.levels.exists() and not test.levels.filter(code=student.level_code).exists():
            is_allowed_to_take = False

        context['is_allowed_to_take'] = is_allowed_to_take
        return context

@custom_login_required_with_token_refresh
def take_test_view(request, test_id):
    """
    Test topshirish sahifasi. Ma'lumotlarni to'liq tayyorlab, shablonga uzatadi.
    Bu yerda ruxsatlar yanada qat'iy tekshiriladi va foydalanuvchi sahifadan chiqarib yuboriladi.
    """
    test = get_object_or_404(Test, pk=test_id)
    student = request.current_student
    now = timezone.now()

    # --- QAT'IY RUXSAT TEKSHIRUVI ---
    error_message = ""
    
    # --- IP MANZILNI ANIQLASH VA KONSOLGA CHIQARISH ---
    client_ip = get_client_ip(request)
    print("\n" + "="*25)
    print(f"!!! DIQQAT: Tizim ko'rayotgan IP manzil: {client_ip} !!!")
    print("="*25 + "\n")
    # ------------------------------------------------

    if test.status != Test.Status.ACTIVE:
        error_message = "Bu test hozir aktiv emas."
    elif not ((test.start_time is None or test.start_time <= now) and (test.end_time is None or test.end_time >= now)):
        error_message = "Testning topshirish vaqti tugagan yoki hali boshlanmagan."
    # `is_ip_allowed` funksiyasidan foydalanish
    elif test.allowed_ips and not is_ip_allowed(client_ip, test.allowed_ips):
        error_message = f"Sizning IP manzilingizga ({client_ip}) bu testni topshirishga ruxsat yo'q."
    elif test.faculties.exists() and not test.faculties.filter(id=student.faculty_id_api).exists():
        error_message = "Sizning fakultetingizga ruxsat berilmagan."
    elif test.specialties.exists() and not test.specialties.filter(id=student.specialty_id_api).exists():
        error_message = "Sizning yo'nalishingizga ruxsat berilmagan."
    elif test.groups.exists() and not test.groups.filter(id=student.group_id_api).exists():
        error_message = "Sizning guruhingizga ruxsat berilmagan."
    elif test.levels.exists() and not test.levels.filter(code=student.level_code).exists():
        error_message = "Sizning kursingizga ruxsat berilmagan."

    if error_message:
        messages.error(request, f"Ruxsat yo'q. Sabab: {error_message}")
        return redirect('auth_app:test-list')

    # Testni takroriy topshirishni tekshirish
    if test.allow_once and SurveyResponse.objects.filter(test=test, student=student, is_completed=True).exists():
        messages.warning(request, "Siz bu testni allaqachon topshirib bo'lgansiz.")
        return redirect('auth_app:test-detail', pk=test.id)

    # Test urinishini (SurveyResponse) yaratish yoki hali tugallanmaganini olish
    response_obj, created = SurveyResponse.objects.get_or_create(
        student=student, test=test, is_completed=False
    )

    # Vaqtni hisoblash
    time_left_seconds = None
    if test.time_limit > 0:
        if created: # Faqat yangi urinish uchun vaqtni belgilaymiz
            response_obj.end_time = now + timezone.timedelta(minutes=test.time_limit)
            response_obj.save(update_fields=['end_time'])
        
        if response_obj.end_time:
            time_left_seconds = max(0, (response_obj.end_time - now).total_seconds())

    # Savollarni olish (aralashtirish bilan birga)
    questions_query = test.questions.prefetch_related('answers')
    questions = questions_query.order_by('?') if test.randomize_questions else questions_query.order_by('order')

    context = {
        'test': test,
        'questions': questions,
        'response': response_obj,
        'time_left_seconds': time_left_seconds,
    }
    return render(request, 'auth_app/take_test.html', context)
# auth_app/views.py

# ... boshqa importlar va funksiyalar ...

# auth_app/views.py

# ... boshqa importlar va funksiyalar ...
@method_decorator(custom_login_required_with_token_refresh, name='dispatch')
class TestResultDetailView(DetailView):
    """Talabaning bitta test bo'yicha yakuniy natijasini ko'rsatish sahifasi."""
    model = SurveyResponse
    template_name = 'auth_app/test_result_detail.html'
    context_object_name = 'result'

    def get_queryset(self):
        """
        Faqat tizimga kirgan talabaga tegishli va yakunlangan natijalarni tekshirish.
        """
        return SurveyResponse.objects.filter(
            student=self.request.current_student,  # Talaba o'z natijalarini ko'radi
            is_completed=True  # Yakunlangan test natijalari
        ).select_related('test', 'student').prefetch_related(
            'student_answers__question__answers',  # Savollar va javoblarni oldindan yuklash
            'student_answers__chosen_answer'        # Samaradorlikni oshiradi
        )

    def get_object(self, queryset=None):
        """
        Ushbu funksiya URL'da berilgan `pk` bo'yicha natijalar tekshirishini tasdiqlaydi.
        """
        try:
            queryset = self.get_queryset() if queryset is None else queryset
            pk = self.kwargs.get('pk')  # URL orqali keluvchi `pk`
            obj = get_object_or_404(queryset, pk=pk)  # Mos natijani topib, qaytaradi yoki 404 chiqaradi
            return obj
        except Http404:
            # Если результат не найден, логируем ошибку для отладки
            logger.error(f"SurveyResponse with pk={pk} not found for student {self.request.current_student.id}")
            raise

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.object
        # Test natijasi haqida qo'shimcha ma'lumotlarni kontekstga qo'shish
        if result:
            percentage = 0
            if result.test.max_score > 0:
                percentage = (float(result.score) / float(result.test.max_score)) * 100
            context['percentage'] = percentage
        return context

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            # Если результат не найден, пишем информативное сообщение
            logger.error(f"SurveyResponse not found: pk={kwargs.get('pk')}, student_id={request.current_student.id}")
            messages.error(request,
                           "Указанный результат теста не найден. Возможно, вы пытаетесь получить доступ к результату другого студента или результат был удален.")
            return redirect('auth_app:test-result-list')


@method_decorator(custom_login_required_with_token_refresh, name='dispatch')
class TestResultListView(ListView):
    """Talabaning barcha yakunlangan test natijalari ro'yxati."""
    model = SurveyResponse
    template_name = 'auth_app/test_result_list.html'
    context_object_name = 'results'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in TestResultListView: {e}, student_id={request.current_student.id}")
            messages.error(request, "При загрузке результатов тестов произошла ошибка. Пожалуйста, попробуйте позже.")
            return render(request, self.template_name, {'results': []})

    def get_queryset(self):
        # Faqat tizimga kirgan talabaning yakunlangan natijalarini olish
        return SurveyResponse.objects.filter(
            student=self.request.current_student,
            is_completed=True
        ).select_related('test').order_by('-end_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Natijalar ro'yxati bo'sh bo'lsa, foydalanuvchiga xabar berish
        if not self.get_queryset().exists():
            messages.info(self.request, "Сиз ҳали бирорта ҳам тестни якунламагансиз.")
        return context