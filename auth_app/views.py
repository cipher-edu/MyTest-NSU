# auth_app/views.py
import logging
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.core.cache import cache
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .decorators import custom_login_required_with_token_refresh
from .forms import LoginForm, TestForm, QuestionForm, AnswerFormSet
from .models import * # Barcha modellarni import qilish
from .services.hemis_api_service import HemisAPIClient, APIClientException
from .utils import map_api_data_to_student_model_defaults, update_student_instance_with_defaults

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
    if 'api_token' in request.session and 'student_db_id' in request.session:
        if _handle_api_token_refresh(request):
            try:
                # Foydalanuvchi hali ham bazada mavjudligini tekshirish
                Student.objects.get(pk=request.session['student_db_id'])
                next_url = request.session.pop('login_next_url', None) or request.GET.get('next')
                return redirect(next_url or 'dashboard')
            except Student.DoesNotExist:
                logger.warning(f"Logged in user (ID: {request.session.get('student_db_id')}) not found in DB. Flushing session.")
                request.session.flush()
                # Bu holatda login formaga qaytamiz
        else:
            # Token yangilash muvaffaqiyatsiz bo'lsa, _handle_api_token_refresh o'zi login sahifasiga
            # yo'naltirishi yoki xabar berishi kerak. Agar yo'naltirmasa, bu yerda:
            return redirect(settings.LOGIN_URL)


    if request.method == 'GET' and 'next' in request.GET:
        request.session['login_next_url'] = request.GET.get('next')

    form = LoginForm(request.POST or None)
    log_id_base = _get_error_log_id()

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        api_client = HemisAPIClient()

        try:
            logger.info(f"Login attempt for user: {username}")
            api_token, refresh_data = api_client.login(username, password) # refresh_data endi dict yoki string bo'lishi mumkin
            
            logger.info(f"Login successful for {username}, fetching account data with new token.")
            student_info_from_api = api_client.get_account_me(api_token_override=api_token)

            if not student_info_from_api or not isinstance(student_info_from_api, dict):
                log_id = f"{log_id_base}_NODATA"
                logger.error(f"Error Log ID: {log_id} - No student data received from API for {username} or data is not a dict. API Response: {str(student_info_from_api)[:250]}")
                messages.error(request, f"API dan ma'lumot olishda xatolik. (Xatolik ID: {log_id})")
                return render(request, 'auth_app/login.html', {'form': form})

            with transaction.atomic():
                student_defaults = map_api_data_to_student_model_defaults(student_info_from_api, username)
                if not student_defaults: # Agar map_api_data_to_student_model_defaults bo'sh qaytarsa
                    raise ValueError("API ma'lumotlarini modellashtirishda xatolik.")

                student, created = Student.objects.update_or_create(
                    username=username,
                    defaults=student_defaults # update_or_create o'zi o'zgarishlarni saqlaydi
                )
            
            request.session['api_token'] = api_token
            request.session['student_db_id'] = student.id
            request.session['username_display'] = str(student)
            
            expires_in_login = settings.SESSION_COOKIE_AGE # default
            refresh_cookie_login = None

            if isinstance(refresh_data, str): # Agar refresh_data to'g'ridan-to'g'ri cookie string bo'lsa
                refresh_cookie_login = refresh_data
            elif isinstance(refresh_data, dict):
                if 'expires_in' in refresh_data:
                    try:
                        expires_in_login = int(refresh_data['expires_in'])
                    except (ValueError, TypeError):
                        logger.warning(f"Login API dan kelgan 'expires_in' ({refresh_data['expires_in']}) yaroqsiz.")
                
                if 'refresh_token_cookie_value' in refresh_data:
                    refresh_cookie_login = refresh_data['refresh_token_cookie_value']
                elif 'refresh_cookie' in refresh_data: # Boshqa nom bilan
                    refresh_cookie_login = refresh_data['refresh_cookie']
                # Agar refresh token to'g'ridan-to'g'ri 'refresh_token' kaliti bilan kelsa:
                # elif 'refresh_token' in refresh_data: 
                #    request.session['hemis_refresh_token_value'] = refresh_data['refresh_token'] # Buni saqlash kerak bo'lsa
            
            request.session['api_token_expiry_timestamp'] = timezone.now().timestamp() + expires_in_login
            
            if refresh_cookie_login:
                request.session['hemis_refresh_cookie'] = refresh_cookie_login
            
            request.session.set_expiry(settings.SESSION_COOKIE_AGE) # Django sessiyasining muddati

            display_name = student_defaults.get('full_name_api') or student.username
            messages.success(request, f"Xush kelibsiz, {display_name}!")
            logger.info(f"User {username} logged in. Session expiry: {request.session.get_expiry_date()}, API token expiry: {timezone.datetime.fromtimestamp(request.session['api_token_expiry_timestamp'])}")
            
            next_url = request.session.pop('login_next_url', None) or request.GET.get('next')
            return redirect(next_url or 'dashboard')

        except APIClientException as e:
            log_id = f"{log_id_base}_APICLI"
            logger.error(
                f"Error Log ID: {log_id} - User: {username}, APIClientException: {e.args[0]}, "
                f"Status: {e.status_code}, API Response: {str(e.response_data)[:250]}, URL: {e.url}",
                exc_info=False
            )
            user_message = str(e.args[0] if e.args else "Noma'lum API xatosi")
            if e.status_code in [400, 401, 403] or \
               (isinstance(user_message, str) and any(term in user_message.lower() for term in ["token", "authentication", "авторизации", "credentials", "login", "parol", "not found", "no active account"])):
                 user_message = "Login yoki parol xato."
            elif e.status_code == 503 or (e.status_code is None and any(term in user_message.lower() for term in ["connection", "ulan", "refused"])):
                user_message = "API serveriga ulanib bo'lmadi. Internet aloqangizni tekshiring yoki keyinroq urinib ko'ring."
            elif e.status_code == 504 or (e.status_code is None and "timeout" in user_message.lower()):
                user_message = "API serveridan javob kutish vaqti tugadi."
            elif e.status_code == 404 and e.url and "/auth/login" in str(e.url):
                 user_message = "Autentifikatsiya xizmati manzili noto'g'ri sozlanган."
            elif not user_message or user_message == "Noma'lum API xatosi":
                 user_message = "API bilan bog'lanishda noma'lum xatolik."

            messages.error(request, f"{user_message} (Xatolik ID: {log_id})")
        
        except ValueError as ve: # Masalan, map_api_data_to_student_model_defaults xatolik qaytarsa
            log_id = f"{log_id_base}_VALERR"
            logger.error(f"Error Log ID: {log_id} - User: {username}, ValueError: {ve}", exc_info=True)
            messages.error(request, f"Ma'lumotlarni qayta ishlashda xatolik. (Xatolik ID: {log_id})")

        except Exception as e:
            log_id = f"{log_id_base}_UNEXP"
            logger.critical(f"Error Log ID: {log_id} - User: {username}, Unexpected error in login_view: {type(e).__name__} - {e}", exc_info=True)
            messages.error(request, f"Noma'lum tizim xatoligi yuz berdi. Iltimos, administratorga murojaat qiling. (Xatolik ID: {log_id})")

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
            return redirect('dashboard')
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



def is_teacher_or_staff(user):
    # Bu yerda o'qituvchilar guruhini ham tekshirish mumkin
    # return user.is_authenticated and (user.is_staff or user.groups.filter(name='Teachers').exists())
    return user.is_authenticated and user.is_staff

teacher_required = user_passes_test(is_teacher_or_staff, login_url='/admin/login/')

# === TALABALAR UCHUN VIEW'LAR ===

@custom_login_required_with_token_refresh
def test_list_view(request):
    """Talabalar uchun aktiv testlar ro'yxati."""
    tests = Test.objects.filter(is_active=True).select_related('creator')
    context = {
        'tests': tests,
    }
    return render(request, 'auth_app/student/test_list.html', context)

@custom_login_required_with_token_refresh
def test_detail_view(request, pk):
    """Testni boshlashdan oldin u haqida ma'lumot."""
    test = get_object_or_404(Test, pk=pk, is_active=True)
    context = {
        'test': test,
    }
    return render(request, 'auth_app/student/test_detail.html', context)

@custom_login_required_with_token_refresh
@transaction.atomic
def start_attempt_view(request, test_id):
    """Test uchun yangi urinish (TestAttempt) yaratadi."""
    if request.method == 'POST':
        test = get_object_or_404(Test, pk=test_id, is_active=True)
        student = request.current_student

        # Agar bu test uchun tugallanmagan urinish bo'lsa, o'shanga yo'naltirish
        active_attempt = TestAttempt.objects.filter(
            student=student,
            test=test,
            status=TestAttempt.AttemptStatus.IN_PROGRESS
        ).first()

        if active_attempt:
            return redirect('take_test', attempt_id=active_attempt.id)

        # Yangi urinish yaratish
        attempt = TestAttempt.objects.create(student=student, test=test)
        return redirect('take_test', attempt_id=attempt.id)
    return redirect('test_detail', pk=test_id)


@custom_login_required_with_token_refresh
def take_test_view(request, attempt_id):
    """Asosiy test topshirish sahifasi."""
    attempt = get_object_or_404(
        TestAttempt.objects.select_related('test'),
        pk=attempt_id,
        student=request.current_student
    )

    if attempt.status == TestAttempt.AttemptStatus.COMPLETED:
        messages.info(request, "Siz bu testni allaqachon tugatgansiz.")
        return redirect('attempt_result', attempt_id=attempt.id)

    time_limit_seconds = attempt.test.time_limit_minutes * 60
    time_elapsed = (timezone.now() - attempt.start_time).total_seconds()
    time_remaining = max(0, time_limit_seconds - time_elapsed) if time_limit_seconds > 0 else -1 # -1 cheksiz degani

    if time_remaining == 0 and time_limit_seconds > 0:
        return redirect('finish_attempt', attempt_id=attempt.id)
        
    questions = attempt.test.questions.all().prefetch_related('answers')

    context = {
        'attempt': attempt,
        'test': attempt.test,
        'questions': questions,
        'time_remaining': time_remaining, # sekundlarda
    }
    return render(request, 'auth_app/student/take_test.html', context)


@custom_login_required_with_token_refresh
@transaction.atomic
def finish_attempt_view(request, attempt_id):
    """Testni tugatish va natijalarni hisoblash."""
    if request.method == 'POST':
        attempt = get_object_or_404(
            TestAttempt,
            pk=attempt_id,
            student=request.current_student,
            status=TestAttempt.AttemptStatus.IN_PROGRESS
        )

        # Javoblarni saqlash
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = key.split('_')[1]
                question = get_object_or_404(Question, pk=question_id)
                student_answer, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question=question)

                # Oldingi javoblarni tozalash
                student_answer.selected_answers.clear()
                
                # Yangi javoblarni qo'shish
                if question.question_type == 'multiple_choice':
                    answer_ids = request.POST.getlist(key)
                    for answer_id in answer_ids:
                        answer = get_object_or_404(Answer, pk=answer_id)
                        student_answer.selected_answers.add(answer)
                else: # single_choice
                    answer = get_object_or_404(Answer, pk=value)
                    student_answer.selected_answers.add(answer)
        
        # Urinishni yakunlash (signal ishga tushadi va hisoblaydi)
        attempt.status = TestAttempt.AttemptStatus.COMPLETED
        attempt.end_time = timezone.now()
        attempt.save() # Bu yerda signal ishga tushadi

        messages.success(request, f"'{attempt.test.title}' testi muvaffaqiyatli yakunlandi!")
        return redirect('attempt_result', attempt_id=attempt.id)
    
    return redirect('take_test', attempt_id=attempt_id)


@custom_login_required_with_token_refresh
def attempt_result_view(request, attempt_id):
    """Talaba uchun test natijalarini ko'rsatish sahifasi."""
    attempt = get_object_or_404(
        TestAttempt.objects.select_related('test', 'student'),
        pk=attempt_id,
        student=request.current_student
    )
    # Javoblarni ham yuklab olish
    student_answers = attempt.student_answers.all().select_related('question').prefetch_related('selected_answers', 'question__answers')

    context = {
        'attempt': attempt,
        'student_answers': student_answers
    }
    return render(request, 'auth_app/student/attempt_result.html', context)

# === O'QITUVCHILAR UCHUN VIEW'LAR ===

@method_decorator(teacher_required, name='dispatch')
class TestListView(ListView):
    """O'qituvchi uchun u yaratgan testlar ro'yxati."""
    model = Test
    template_name = 'auth_app/teacher/test_management_list.html'
    context_object_name = 'tests'

    def get_queryset(self):
        # Faqat o'zi yaratgan testlarni ko'rsatish
        return Test.objects.filter(creator=self.request.user).order_by('-created_at')

@method_decorator(teacher_required, name='dispatch')
class TestCreateView(CreateView):
    model = Test
    form_class = TestForm
    template_name = 'auth_app/teacher/test_form.html'
    success_url = reverse_lazy('teacher_test_list')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        messages.success(self.request, "Test muvaffaqiyatli yaratildi.")
        return super().form_valid(form)

@method_decorator(teacher_required, name='dispatch')
class TestUpdateView(UpdateView):
    model = Test
    form_class = TestForm
    template_name = 'auth_app/teacher/test_form.html'
    success_url = reverse_lazy('teacher_test_list')

    def get_queryset(self):
        return Test.objects.filter(creator=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Test muvaffaqiyatli yangilandi.")
        return super().form_valid(form)
        
@method_decorator(teacher_required, name='dispatch')
class TestDeleteView(DeleteView):
    model = Test
    template_name = 'auth_app/teacher/test_confirm_delete.html'
    success_url = reverse_lazy('teacher_test_list')
    
    def get_queryset(self):
        return Test.objects.filter(creator=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, "Test muvaffaqiyatli o'chirildi.")
        return super().form_valid(form)

@teacher_required
def manage_questions_view(request, test_id):
    """Test uchun savollarni qo'shish, tahrirlash va o'chirish."""
    test = get_object_or_404(Test, pk=test_id, creator=request.user)
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST, request.FILES)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.test = test
            question.save()
            
            # Formset'ni question bilan bog'lab qayta yaratish
            formset = AnswerFormSet(request.POST, instance=question)
            if formset.is_valid():
                formset.save()
                messages.success(request, f"'{question.text[:30]}...' savoli muvaffaqiyatli qo'shildi.")
                return redirect('manage_questions', test_id=test.id)
            else:
                 # Agar formset yaroqsiz bo'lsa, xatolik bilan qaytarish
                messages.error(request, "Javob variantlarini to'ldirishda xatolik.")
        else:
            formset = AnswerFormSet() # Bo'sh formset
            messages.error(request, "Savolni to'ldirishda xatolik.")

    else:
        question_form = QuestionForm()
        formset = AnswerFormSet()
        
    questions = test.questions.all().prefetch_related('answers')
    context = {
        'test': test,
        'questions': questions,
        'question_form': question_form,
        'formset': formset
    }
    return render(request, 'auth_app/teacher/manage_questions.html', context)