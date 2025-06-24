// static/admin/js/survey_question_choices.js (misol uchun jQuery bilan)
(function($) {
    $(document).ready(function() {
        function toggleChoiceInlines(questionBlock) {
            var questionTypeSelect = questionBlock.find('select[name$="-question_type"]');
            var choiceInlineGroup = questionBlock.find('.inline-group').filter(function() {
                // ChoiceInline group ni aniqroq topish kerak bo'lishi mumkin
                return $(this).find('input[name*="-choice_set-"]').length > 0; 
            });

            if (questionTypeSelect.val() === 'text' || questionTypeSelect.val() === '') {
                choiceInlineGroup.hide();
            } else {
                choiceInlineGroup.show();
            }
        }

        // Mavjud Question bloklari uchun
        $('.inline-related[id*="question_set-"]').each(function() {
            var questionBlock = $(this);
            toggleChoiceInlines(questionBlock); // Sahifa yuklanganda tekshirish
            questionBlock.find('select[name$="-question_type"]').on('change', function() {
                toggleChoiceInlines(questionBlock); // O'zgarish bo'lganda tekshirish
            });
        });

        // Dinamik qo'shilgan Question bloklari uchun (Django admin "Add another Question" dan keyin)
        $(document).on('formset:added', function(event, $row, formsetName) {
            if (formsetName.includes('question_set')) {
                var questionBlock = $row;
                toggleChoiceInlines(questionBlock);
                questionBlock.find('select[name$="-question_type"]').on('change', function() {
                    toggleChoiceInlines(questionBlock);
                });
            }
        });
    });
})(django.jQuery);