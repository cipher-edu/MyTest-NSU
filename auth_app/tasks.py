# auth_app/tasks.py
from celery import shared_task
from django.conf import settings
from django.db import transaction
import logging
import re
from .models import Test, Question, Answer

logger = logging.getLogger(__name__)

def parse_test_file_content(file_content):
    """
    .txt fayl matnini o'qib, savol va javoblar ro'yxatini qaytaradi.
    Bu versiya mustahkam bo'lib, ajratuvchilar atrofidagi ortiqcha bo'shliqlar
    kabi turli formatlashdagi nomuvofiqliklarni ham ishlay oladi.
    """
    questions_data = []
    
    # Qator tugashlarini normallashtirish va butun faylning bosh/oxiridagi bo'shliqlarni olib tashlash
    content = file_content.replace('\r\n', '\n').strip()
    
    if not content:
        return []

    # Matnni savol bloklariga moslashuvchan regex yordamida ajratish.
    question_blocks = re.split(r'\s*\n\s*=\s*\n\s*', content)
    
    for block in question_blocks:
        block_content = block.strip()
        if not block_content:
            continue
            
        lines = [line.strip() for line in block_content.split('\n') if line.strip()]
        
        if len(lines) < 2:
            continue

        question_text = lines[0]
        answers = []
        correct_answer_found = False
        
        for line in lines[1:]:
            if not line:
                continue

            is_correct = False
            answer_text = ''

            if line.startswith('#'):
                is_correct = True
                correct_answer_found = True
                answer_text = line[1:].strip()
            elif line.startswith('+'):
                is_correct = False
                answer_text = line[1:].strip()
            else:
                continue

            if answer_text:
                answers.append({
                    'text': answer_text,
                    'is_correct': is_correct
                })

        if question_text and answers and correct_answer_found:
            questions_data.append({
                'question': question_text,
                'answers': answers,
                'points': 1
            })
            
    return questions_data


@shared_task(bind=True, name='auth_app.tasks.process_test_file')
def process_test_file_task(self, test_id):
    try:
        test = Test.objects.get(id=test_id)
    except Test.DoesNotExist:
        logger.error(f"Celery vazifasi uchun Test (ID: {test_id}) topilmadi.")
        return f"Test ID {test_id} not found."

    if not test.source_file:
        logger.error(f"Test (ID: {test_id}) uchun manba fayl topilmadi.")
        test.status = Test.Status.DRAFT
        test.save(update_fields=['status'])
        return f"Fayl topilmadi."

    try:
        file_content = test.source_file.read().decode('utf-8')
        questions_data = parse_test_file_content(file_content)

        if not questions_data:
            logger.warning(f"Fayldan (Test ID: {test_id}) hech qanday savol o'qib bo'lmadi. Fayl bo'sh yoki formati noto'g'ri.")
            test.status = Test.Status.DRAFT
            test.save(update_fields=['status'])
            return "Fayldan savollar topilmadi."

        questions_created_count = 0
        with transaction.atomic():
            # Eski savollarni o'chirish (agar fayl qayta yuklansa)
            test.questions.all().delete()
            logger.info(f"Test (ID: {test.id}) uchun eski savollar o'chirildi.")

            # Savol va javoblarni birma-bir yaratish
            for i, q_data in enumerate(questions_data):
                question = Question.objects.create(
                    test=test,
                    text=q_data['question'],
                    points=q_data.get('points', 1),
                    order=i + 1
                )
                questions_created_count += 1

                for a_data in q_data['answers']:
                    Answer.objects.create(
                        question=question,
                        text=a_data['text'],
                        is_correct=a_data['is_correct']
                    )
            
            logger.info(f"Tranzaksiya ichida {questions_created_count} ta savol va ularning javoblari yaratildi.")

        # Jarayon tugagach, test statusini "Qoralama" ga o'tkazamiz
        test.status = Test.Status.DRAFT
        test.save(update_fields=['status'])
        
        logger.info(f"{questions_created_count} ta savol Test (ID: {test_id}) uchun muvaffaqiyatli yaratildi.")
        return f"Successfully created {questions_created_count} questions for Test ID {test_id}."

    except Exception as e:
        logger.error(f"Test faylini (ID: {test_id}) qayta ishlashda kutilmagan xatolik: {e}", exc_info=True)
        # Xatolik yuz bersa, test statusini yana "Qoralama" ga qaytarib, xabar beramiz
        test.status = Test.Status.DRAFT
        test.save(update_fields=['status'])
        raise self.retry(exc=e, countdown=60)