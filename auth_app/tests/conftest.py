import pytest
from faker import Faker
from auth_app.models import Student, Survey, Question, Choice

# Faker obyektini yaratish (o'zbek tilidagi ma'lumotlar uchun)
fake = Faker('uz_UZ') 

@pytest.fixture
def student_user(db) -> Student:
    """Haqiqiyga o'xshash bitta Student obyektini yaratadi."""
    profile = fake.profile(fields=['username', 'name', 'mail'])
    first_name, last_name = profile['name'].split(' ', 1)
    
    student, _ = Student.objects.update_or_create(
        username=profile['username'],
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'email': profile['mail'],
            'student_id_number': str(fake.unique.random_number(digits=12)),
        }
    )
    return student

@pytest.fixture
def survey_with_questions(db) -> Survey:
    """Har xil turdagi savollarga ega so'rovnoma yaratadi."""
    survey = Survey.objects.create(title=fake.sentence(nb_words=4))

    # Yagona tanlovli savol
    q1 = Question.objects.create(survey=survey, text="Sevimli rangingiz qaysi?", question_type='single_choice')
    Choice.objects.create(question=q1, text="Qizil")
    Choice.objects.create(question=q1, text="Yashil")
    Choice.objects.create(question=q1, text="Ko'k")

    # Ko'p tanlovli savol
    q2 = Question.objects.create(survey=survey, text="Qaysi sport turlarini yoqtirasiz?", question_type='multiple_choice')
    Choice.objects.create(question=q2, text="Futbol")
    Choice.objects.create(question=q2, text="Basketbol")
    Choice.objects.create(question=q2, text="Kurash")

    # Matnli savol
    Question.objects.create(survey=survey, text="Dasturlash haqida fikringiz?", question_type='text')
    
    return survey