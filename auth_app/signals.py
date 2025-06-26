# auth_app/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TestAttempt, StudentAnswer, Question

@receiver(post_save, sender=TestAttempt)
def calculate_test_results(sender, instance, created, **kwargs):
    """
    TestAttempt holati "Tugatilgan"ga o'zgarganda natijalarni avtomatik hisoblaydi.
    """
    if not created and instance.status == TestAttempt.AttemptStatus.COMPLETED and instance.score == 0:
        
        total_points_possible = 0
        total_points_earned = 0

        # Birinchi, har bir javobni tekshirib, ballarni hisoblaymiz
        student_answers = instance.student_answers.all().select_related('question').prefetch_related('selected_answers')
        
        for sa in student_answers:
            question = sa.question
            correct_answers = set(question.answers.filter(is_correct=True))
            selected_answers = set(sa.selected_answers.all())

            # Savolning to'g'riligini tekshirish
            if correct_answers == selected_answers:
                sa.is_correct = True
                sa.points_earned = question.points
            else:
                sa.is_correct = False
                sa.points_earned = 0
            
            sa.save(update_fields=['is_correct', 'points_earned'])
            total_points_earned += sa.points_earned

        # Testdagi umumiy mumkin bo'lgan ballarni hisoblash
        all_questions = instance.test.questions.all()
        for q in all_questions:
            total_points_possible += q.points

        # Yakuniy natijani TestAttempt'ga yozish
        instance.score = total_points_earned
        
        if total_points_possible > 0:
            instance.percentage = round((total_points_earned / total_points_possible) * 100, 2)
        else:
            instance.percentage = 0
            
        instance.passed = instance.percentage >= instance.test.pass_percentage
        
        # Signal qayta ishga tushmasligi uchun update_fields ishlatamiz
        TestAttempt.objects.filter(pk=instance.pk).update(
            score=instance.score,
            percentage=instance.percentage,
            passed=instance.passed
        )