# auth_app/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TestAttempt, StudentAnswer, Question
from typing import Set

def _check_single_choice(question, selected_answers: Set):
    correct_answers = set(question.answers.filter(is_correct=True))
    return selected_answers == correct_answers, question.points if selected_answers == correct_answers else 0

def _check_multiple_choice(question, selected_answers: Set):
    correct_answers = set(question.answers.filter(is_correct=True))
    if not correct_answers:
        return False, 0
    # Qisman to'g'ri javoblar uchun ball: to'g'ri tanlanganlar nisbati
    true_positives = len(selected_answers & correct_answers)
    false_positives = len(selected_answers - correct_answers)
    false_negatives = len(correct_answers - selected_answers)
    if true_positives == len(correct_answers) and false_positives == 0:
        return True, question.points
    # Qisman ball: faqat to'g'ri tanlanganlar uchun, noto'g'ri tanlanganlar uchun jarima
    partial_score = max(0, question.points * (true_positives - false_positives) / len(correct_answers))
    return False, round(partial_score, 2)

def _check_open_text(question, open_answer_text: str):
    # TODO: Ochiq savollar uchun avtomatik yoki manual baholash hook
    # Hozircha ball 0, is_correct False
    return False, 0

@receiver(post_save, sender=TestAttempt)
def calculate_test_results(sender, instance, created, **kwargs):
    """
    TestAttempt holati "Tugatilgan"ga o'zgarganda natijalarni avtomatik hisoblaydi.
    """
    if not created and instance.status == TestAttempt.AttemptStatus.COMPLETED and instance.score == 0:
        total_points_possible = 0
        total_points_earned = 0
        student_answers = instance.student_answers.all().select_related('question').prefetch_related('selected_answers')
        for sa in student_answers:
            question = sa.question
            if question.question_type == question.QuestionType.SINGLE:
                is_correct, points = _check_single_choice(question, set(sa.selected_answers.all()))
            elif question.question_type == question.QuestionType.MULTIPLE:
                is_correct, points = _check_multiple_choice(question, set(sa.selected_answers.all()))
            elif question.question_type == question.QuestionType.OPEN:
                is_correct, points = _check_open_text(question, sa.open_answer_text)
            else:
                is_correct, points = False, 0
            sa.is_correct = is_correct
            sa.points_earned = points
            sa.save(update_fields=['is_correct', 'points_earned'])
            total_points_earned += points
        all_questions = instance.test.questions.all()
        for q in all_questions:
            total_points_possible += q.points
        instance.score = total_points_earned
        if total_points_possible > 0:
            instance.percentage = round((total_points_earned / total_points_possible) * 100, 2)
        else:
            instance.percentage = 0
        instance.passed = instance.percentage >= instance.test.pass_percentage
        TestAttempt.objects.filter(pk=instance.pk).update(
            score=instance.score,
            percentage=instance.percentage,
            passed=instance.passed
        )