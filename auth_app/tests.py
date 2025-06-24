from auth_app.models import SurveyResponse, Answer
response = SurveyResponse.objects.filter(survey__id=2).last()
print(response.student)
answers = response.answers.all()
for answer in answers:
    print(f"Question: {answer.question.text}, Answer: {answer}")