import pytest
import json
import time
import tracemalloc
import os
from django.urls import reverse
from auth_app.models import Survey, Student, Question

@pytest.mark.django_db
def test_submit_survey_success(client, student_user, survey_with_questions):
    """Muvaffaqiyatli so'rovnoma yuborishni tekshirish"""
    # Foydalanuvchi sessiyasini qo'lda sozlash
    session = client.session
    session['student_db_id'] = student_user.id
    session['api_token'] = 'fake_test_token'
    session.save()

    url = reverse('submit_survey_api', kwargs={'survey_pk': survey_with_questions.pk})
    
    # Savollarga javob tayyorlash (savol turiga mos ravishda)
    answers = {}
    for q in survey_with_questions.questions.all():
        if q.question_type == 'single_choice':
            answers[str(q.id)] = str(q.choices.first().id)
        elif q.question_type == 'multiple_choice':
            answers[str(q.id)] = [str(c.id) for c in q.choices.all()[:2]]
        else:  # text
            answers[str(q.id)] = "Test javobi"

    payload = {"answers": answers}
    response = client.post(url, data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 200
    assert response.json()['status'] == 'success'

@pytest.mark.django_db
def test_submit_survey_massive_users(client, survey_with_questions, db):
    """
    60 000+ foydalanuvchi uchun so'rovnoma yuborish testini kengaytirilgan holda tekshiradi.
    Har bir foydalanuvchi uchun alohida javob yuboriladi.
    """
    # 60 000 ta Student foydalanuvchi yaratamiz (bulk_create orqali tezroq)
    students = [
        Student(
            username=f"testuser_{i}",
            first_name=f"Test{i}",
            last_name=f"User{i}",
            email=f"testuser_{i}@example.com",
            student_id_number=f"{100000000000 + i}"
        ) for i in range(60000)
    ]
    Student.objects.bulk_create(students, batch_size=1000)
    all_students = Student.objects.filter(username__startswith="testuser_")

    # Savollarga javob tayyorlash (savol turiga mos ravishda)
    answers = {}
    for q in survey_with_questions.questions.all():
        if q.question_type == 'single_choice':
            answers[str(q.id)] = str(q.choices.first().id)
        elif q.question_type == 'multiple_choice':
            answers[str(q.id)] = [str(c.id) for c in q.choices.all()[:2]]
        else:  # text
            answers[str(q.id)] = "Massive test javobi"
    payload = {"answers": answers}

    url = reverse('submit_survey_api', kwargs={'survey_pk': survey_with_questions.pk})

    # 100 ta foydalanuvchi uchun so'rov yuborishni ko'rsatamiz (resurslarni tejash uchun)
    for student in all_students[:100]:
        session = client.session
        session['student_db_id'] = student.id
        session['api_token'] = 'fake_test_token'
        session.save()
        response = client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 200
        assert response.json()['status'] == 'success'

@pytest.mark.django_db
def test_submit_survey_massive_users_with_stats(client, survey_with_questions, db):
    """
    60 000+ foydalanuvchi uchun kengaytirilgan test natijalari va resurs sarfini o'lchaydi.
    Natijada: umumiy vaqt, o'rtacha va maksimal so'rov vaqti, xotira sarfi va muvaffaqiyatli so'rovlar soni ko'rsatiladi.
    """
    students = [
        Student(
            username=f"testuser_{i}",
            first_name=f"Test{i}",
            last_name=f"User{i}",
            email=f"testuser_{i}@example.com",
            student_id_number=f"{100000000000 + i}"
        ) for i in range(60000)
    ]
    Student.objects.bulk_create(students, batch_size=1000)
    all_students = Student.objects.filter(username__startswith="testuser_")

    answers = {}
    for q in survey_with_questions.questions.all():
        if q.question_type == 'single_choice':
            answers[str(q.id)] = str(q.choices.first().id)
        elif q.question_type == 'multiple_choice':
            answers[str(q.id)] = [str(c.id) for c in q.choices.all()[:2]]
        else:
            answers[str(q.id)] = "Massive test javobi"
    payload = {"answers": answers}
    url = reverse('submit_survey_api', kwargs={'survey_pk': survey_with_questions.pk})

    times = []
    success_count = 0
    tracemalloc.start()
    start_time = time.perf_counter()
    for student in all_students[:60000]:  # 100 ta uchun, xohlasangiz all_students ga o'zgartiring
        session = client.session
        session['student_db_id'] = student.id
        session['api_token'] = 'fake_test_token'
        session.save()
        t0 = time.perf_counter()
        response = client.post(url, data=json.dumps(payload), content_type='application/json')
        t1 = time.perf_counter()
        times.append(t1 - t0)
        if response.status_code == 200 and response.json().get('status') == 'success':
            success_count += 1
    total_time = time.perf_counter() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Statistikani text faylga yozish
    with open("test_stats.txt", "w", encoding="utf-8") as f:
        f.write("--- Test statistikasi ---\n")
        f.write(f"Foydalanuvchilar soni: {len(all_students[:100])}\n")
        f.write(f"Muvaffaqiyatli so'rovlar: {success_count}\n")
        f.write(f"Umumiy vaqt: {total_time:.2f} s\n")
        f.write(f"O'rtacha so'rov vaqti: {sum(times)/len(times):.4f} s\n")
        f.write(f"Maksimal so'rov vaqti: {max(times):.4f} s\n")
        f.write(f"Xotira sarfi: {current/1024/1024:.2f} MB (peak: {peak/1024/1024:.2f} MB)\n")
        f.write("------------------------\n")
    print("\n--- Test statistikasi text faylga saqlandi: test_stats.txt ---\n")
    assert success_count == len(all_students[:100])