import random
from locust import HttpUser, task, between, events
from locust.exception import StopUser
import logging

TEST_USERS = [
    {"username": "testuser1", "password": "password123"},
    {"username": "testuser2", "password": "password123"},
    {"username": "testuser3", "password": "password123"},
]

if not TEST_USERS:
    logging.error("TEST_USERS ro'yxati bo'sh. Test uchun kamida bitta foydalanuvchi kiriting.")
    exit(1)

class SurveyUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 3)

def on_start(self):
    creds = random.choice(TEST_USERS)
    self.client.get("/login/", name="/login [GET]")
    csrf_cookie_name = "hemis_csrf_token"
    if csrf_cookie_name not in self.client.cookies:
        logging.error(f"Login sahifasidan '{csrf_cookie_name}' nomli CSRF token olinmadi. Cookie'lar: {self.client.cookies}")
        raise StopUser("CSRF token topilmadi.")
    csrf_token = self.client.cookies[csrf_cookie_name]
    res = self.client.post(
        "/login/",
        data={
            "username": creds["username"],
            "password": creds["password"],
            "csrfmiddlewaretoken": csrf_token
        },
        name="/login [POST]"
    )
    if res.status_code != 302:
        logging.error(f"Foydalanuvchi '{creds['username']}' tizimga kira olmadi. Status: {res.status_code}, URL: {res.url}, Matn: {res.text[:200]}")
        raise StopUser("Login muvaffaqiyatsiz.")
    else:
        logging.error(f"Aktiv so'rovnomalarni olib bo'lmadi. Status: {response.status_code}")
        self.survey_ids = []
    @task
    def view_and_submit_random_survey(self):
        if not self.survey_ids:
            self.interrupt(reschedule=False)
            return
        survey_pk = random.choice(self.survey_ids)
        with self.client.get(f"/surveys/{survey_pk}/", name="/surveys/[pk]") as response:
            if response.status_code != 200:
                return
        answers_payload = {
            "answers": {
                "1": "Locust test javobi",
                "2": ["1", "3"],
                "3": "5"
            }
        }
        headers = {'X-CSRFToken': self.client.cookies.get('csrftoken', '')}
        self.client.post(
            f"/api/surveys/{survey_pk}/submit/",
            json=answers_payload,
            headers=headers,
            name="/api/surveys/[pk]/submit/"
        )