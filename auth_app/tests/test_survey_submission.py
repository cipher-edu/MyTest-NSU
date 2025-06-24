import pytest
import json
from django.urls import reverse
from auth_app.models import SurveyResponse, Answer

@pytest.mark.django_db
def test_full_survey_submission(client, student_user, survey_with_questions):
    """
    To'liq so'rovnoma yuborish jarayonini tekshiradi:
    1. Foydalanuvchi tizimga kiradi.
    2. API orqali javoblarni yuboradi.
    3. Javoblar ma'lumotlar bazasiga to'g'ri saqlanganini tekshiradi.
    """
    # Foydalanuvchi tizimga kirganini simulyatsiya qilish uchun
    # Django'ning standart `User` modeli bilan bog'liq bo'lsa, client.force_login() ishlatiladi.
    # Bizning holatda, sessiyani qo'lda o'rnatamiz.
    session = client.session
    session['student_db_id'] = student_user.id
    session['api_token'] = 'fake_test_token' 
    session.save()

    # Javoblarni tayyorlash
    answers_payload = {"answers": {}}
    q1 = survey_with_questions.questions.get(question_type='single_choice')
    q2 = survey_with_questions.questions.get(question_type='multiple_choice')
    q3 = survey_with_questions.questions.get(question_type='text')

    # Har bir savol turiga mos javob beramiz
    answers_payload['answers'][str(q1.id)] = str(q1.choices.first().id) # Birinchi variantni tanlaymiz
    answers_payload['answers'][str(q2.id)] = [str(c.id) for c in q2.choices.all()[:2]] # Dastlabki 2 ta variant
    answers_payload['answers'][str(q3.id)] = "Bu PyTest orqali yuborilgan test javobi."

    url = reverse('submit_survey_api', kwargs={'survey_pk': survey_with_questions.pk})
    
    # API'ga POST so'rovini yuborish
    response = client.post(
        url,
        data=json.dumps(answers_payload),
        content_type='application/json'
    )

    # 1. Javob muvaffaqiyatli ekanligini tekshirish
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # 2. Ma'lumotlar bazasiga yozilganini tekshirish
    assert SurveyResponse.objects.filter(survey=survey_with_questions, student=student_user).exists()
    response_obj = SurveyResponse.objects.get(survey=survey_with_questions, student=student_user)
    
    # 3. Har bir javobni alohida tekshirish
    assert Answer.objects.filter(survey_response=response_obj, question=q1).count() == 1
    assert Answer.objects.get(survey_response=response_obj, question=q1).selected_choice == q1.choices.first()
    
    assert Answer.objects.get(survey_response=response_obj, question=q2).selected_choices.count() == 2
    
    assert Answer.objects.get(survey_response=response_obj, question=q3).text_answer == "Bu PyTest orqali yuborilgan test javobi."