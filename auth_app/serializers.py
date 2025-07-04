# auth_app/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import Test, Question, Answer, SurveyResponse, StudentAnswer, Student

class AnswerSerializer(serializers.ModelSerializer):
    """Javob variantlarini serializatsiya qilish uchun (to'g'ri javobni yashirgan holda)."""
    class Meta:
        model = Answer
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    """Savollarni javob variantlari bilan birga serializatsiya qilish."""
    answers = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'points', 'answers']
    
    def get_answers(self, obj):
        # Agar testda javoblarni aralashtirish yoqilgan bo'lsa, javoblarni tasodifiy tartibda qaytaramiz
        if obj.test.randomize_questions:
            answers = obj.answers.all().order_by('?')
        else:
            answers = obj.answers.all()
        return AnswerSerializer(answers, many=True).data


class TestListSerializer(serializers.ModelSerializer):
    """Testlar ro'yxati uchun yengil serializator."""
    question_count = serializers.IntegerField(source='questions.count', read_only=True)
    
    class Meta:
        model = Test
        fields = ['id', 'title', 'description', 'time_limit', 'question_count', 'start_time', 'end_time']

class TestDetailSerializer(TestListSerializer):
    """Testning to'liq ma'lumotlari, savollari bilan birga."""
    questions = serializers.SerializerMethodField()

    class Meta(TestListSerializer.Meta):
        fields = TestListSerializer.Meta.fields + ['questions', 'randomize_questions']

    def get_questions(self, obj):
        # Agar testda savollarni aralashtirish yoqilgan bo'lsa
        if obj.randomize_questions:
            questions = obj.questions.all().order_by('?')
        else:
            questions = obj.questions.all().order_by('order')
        return QuestionSerializer(questions, many=True, context=self.context).data

class StudentAnswerSubmitSerializer(serializers.Serializer):
    """Talaba tomonidan yuborilgan javobni validatsiya qilish uchun."""
    question_id = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    answer_id = serializers.PrimaryKeyRelatedField(queryset=Answer.objects.all())

    def validate(self, data):
        """Javobning savolga tegishli ekanligini tekshirish."""
        if data['answer_id'].question != data['question_id']:
            raise serializers.ValidationError("Tanlangan javob bu savolga tegishli emas.")
        return data

class TestResultSerializer(serializers.ModelSerializer):
    """Test natijalarini ko'rsatish uchun serializator."""
    test = TestListSerializer(read_only=True)
    max_score = serializers.FloatField(source='test.max_score', read_only=True)

    class Meta:
        model = SurveyResponse
        fields = ['id', 'test', 'score', 'max_score', 'start_time', 'end_time', 'is_completed']
        
# --- Admin uchun serializatorlar ---

class AdminStudentAnswerSerializer(serializers.ModelSerializer):
    """Admin uchun talabaning javobini to'liq ko'rsatish."""
    question_text = serializers.CharField(source='question.text', read_only=True)
    chosen_answer_text = serializers.CharField(source='chosen_answer.text', read_only=True, default="Javob berilmagan")
    is_correct = serializers.BooleanField(source='chosen_answer.is_correct', read_only=True)

    class Meta:
        model = StudentAnswer
        fields = ['question_text', 'chosen_answer_text', 'is_correct']

class AdminTestResultDetailSerializer(serializers.ModelSerializer):
    """Admin uchun natijalarni to'liq ko'rish."""
    student = serializers.StringRelatedField()
    test = serializers.StringRelatedField()
    student_answers = AdminStudentAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyResponse
        fields = ['id', 'student', 'test', 'score', 'start_time', 'end_time', 'is_completed', 'student_answers']