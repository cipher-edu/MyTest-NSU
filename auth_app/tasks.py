from celery import shared_task
from django.conf import settings
from django.utils import timezone
import logging
from .services.hemis_api_service import HemisAPIClient, APIClientException
from .models import Student
from .utils import map_api_data_to_student_model_defaults, update_student_instance_with_defaults

logger = logging.getLogger(__name__)

@shared_task(bind=True, name='auth_app.tasks.sync_student_profile_from_api', max_retries=3, default_retry_delay=60 * 5)
def sync_student_profile_from_api(self, student_id, api_token=None):
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        logger.error(f"Student with ID {student_id} not found in Celery task. Task will not retry.")
        return f"Student ID {student_id} not found."
    
    effective_api_token = api_token
    api_source_description = f"provided token for student {student.username}"

    if not effective_api_token:
        if hasattr(settings, 'HEMIS_SYSTEM_API_TOKEN') and settings.HEMIS_SYSTEM_API_TOKEN:
             effective_api_token = settings.HEMIS_SYSTEM_API_TOKEN
             api_source_description = f"system token for student {student.username} (ID: {student.student_id_number or student.username})"
             logger.warning(f"Using HEMIS_SYSTEM_API_TOKEN for task, but get_account_me() might fetch system user's data, not student's, unless API is specifically designed for it or client uses student_id_number with this token.")
        else:
            logger.error(f"No API token provided for student ID {student_id} (username: {student.username}) in Celery task, and no system token configured.")
            return f"API token required for student ID {student_id}."
    
    try:
        client = HemisAPIClient(api_token=effective_api_token)
        student_info_from_api = client.get_account_me()

        if student_info_from_api and isinstance(student_info_from_api, dict):
            defaults = map_api_data_to_student_model_defaults(
                student_info_from_api, 
                student.username
            )
            if defaults:
                update_student_instance_with_defaults(student, defaults)
                logger.info(f"Successfully updated profile using {api_source_description} via Celery task.")
                return f"Student ID {student_id} updated."
            else:
                logger.warning(f"Could not map API data for student ID {student_id} in Celery task. API data: {str(student_info_from_api)[:200]}")
                return f"Failed to map API data for student ID {student_id}."
        elif not student_info_from_api:
            logger.warning(f"No data received from API for student ID {student_id} (username: {student.username}) using {api_source_description} in Celery task.")
            return f"No API data for student ID {student_id}."
        else:
            logger.warning(f"Received non-dict data from API for student ID {student_id} using {api_source_description} in Celery task: {str(student_info_from_api)[:100]}")
            return f"Invalid API data type for student ID {student_id}."
    except APIClientException as e:
        logger.error(f"APIClientException for student ID {student_id} (username: {student.username}) using {api_source_description} in Celery task: {e.args[0]} (Status: {e.status_code})", exc_info=True)
        try:
            if e.status_code in [401, 403]:
                logger.warning(f"Token-related API error ({e.status_code}) for student {student.username}. Not retrying.")
                return f"Token error for student {student.username}."
            raise self.retry(exc=e, countdown=int(self.default_retry_delay * (2 ** self.request.retries)))
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for student ID {student_id} (username: {student.username}) in Celery task after APIClientException.")
            return f"Max retries for student {student.username} (APIClientException)."
    except Exception as e:
        logger.error(f"Unexpected error updating student ID {student_id} (username: {student.username}) using {api_source_description} in Celery task: {e}", exc_info=True)
        try:
            raise self.retry(exc=e, countdown=int(self.default_retry_delay * (2 ** self.request.retries)))
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for student ID {student_id} (username: {student.username}) in Celery task after unexpected error.")
            return f"Max retries for student {student.username} (unexpected error)."