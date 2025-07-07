# auth_app/serializers.py

from rest_framework import serializers
from .models import *

# --- Ma'lumotnomalar uchun yengil Serializer'lar ---
class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'name']

class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ['id', 'name']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['code', 'name']


# --- Talabalar uchun Serializer'lar ---
class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = ['id', 'text', 'points', 'answers']

class TestListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source='questions.count', read_only=True)
    max_score = serializers.IntegerField(read_only=True)
    class Meta:
        model = Test
        fields = ['id', 'title', 'description', 'time_limit', 'question_count', 'max_score']

class TestDetailSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    class Meta:
        model = Test
        fields = ['id', 'title', 'description', 'time_limit', 'randomize_questions', 'questions']

    def get_questions(self, obj):
        questions = obj.questions.order_by('?') if obj.randomize_questions else obj.questions.order_by('order')
        return QuestionSerializer(questions.prefetch_related('answers'), many=True).data

class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'username', 'full_name_api', 'faculty_id_api', 'specialty_id_api', 'group_id_api', 'level_code']

class TestTakingDataSerializer(serializers.Serializer):
    test = TestDetailSerializer(read_only=True)
    student = StudentProfileSerializer(read_only=True)
    time_left_seconds = serializers.IntegerField(read_only=True, allow_null=True)
    response_id = serializers.IntegerField(read_only=True)

class StudentAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    answer_id = serializers.PrimaryKeyRelatedField(queryset=Answer.objects.all())

    def validate(self, data):
        if data['answer_id'].question_id != data['question_id'].id:
            raise serializers.ValidationError({'answer_id': "Tanlangan javob bu savolga tegishli emas."})
        return data

class TestResultSerializer(serializers.ModelSerializer):
    test = TestListSerializer(read_only=True)
    max_score = serializers.IntegerField(source='test.max_score', read_only=True)
    class Meta:
        model = SurveyResponse
        fields = ['id', 'test', 'score', 'max_score', 'start_time', 'end_time']


# --- Admin uchun Serializer'lar ---

class AdminStudentAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    chosen_answer_text = serializers.CharField(source='chosen_answer.text', read_only=True, default="Javob berilmagan")
    is_correct = serializers.BooleanField(source='chosen_answer.is_correct', read_only=True, default=False)
    
    class Meta:
        model = StudentAnswer
        fields = ['question_text', 'chosen_answer_text', 'is_correct']

# BU CLASS NOMI MUHIM!
class AdminSurveyResponseSerializer(serializers.ModelSerializer):
    student = StudentProfileSerializer(read_only=True)
    test = TestListSerializer(read_only=True)
    student_answers = AdminStudentAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyResponse
        fields = ['id', 'student', 'test', 'score', 'start_time', 'end_time', 'is_completed', 'student_answers']

class AdminTestDetailSerializer(serializers.ModelSerializer):
    faculties = FacultySerializer(many=True, read_only=True)
    specialties = SpecialtySerializer(many=True, read_only=True)
    groups = GroupSerializer(many=True, read_only=True)
    levels = LevelSerializer(many=True, read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = '__all__'