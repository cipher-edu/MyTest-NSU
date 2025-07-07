    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.object
        # Test natijasi haqida qo'shimcha ma'lumotlarni kontekstga qo'shish
        if result:
            percentage = 0
            if result.test.max_score > 0:
                percentage = (float(result.score) / float(result.test.max_score)) * 100
            context['percentage'] = percentage
        return context

            def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            # Если результат не найден, пишем информативное сообщение
            logger.error(f"SurveyResponse not found: pk={kwargs.get('pk')}, student_id={request.current_student.id}")
            messages.error(request, "Указанный результат теста не найден. Возможно, вы пытаетесь получить доступ к результату другого студента или результат был удален.")
            return redirect('auth_app:test-result-list')
