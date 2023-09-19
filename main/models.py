from django.db import models
from django.utils.safestring import mark_safe


# Модель Архетипов
class Archetype(models.Model):
    archetype_name = models.CharField(max_length=255, verbose_name = "Название архетипа")  # Название архетипа
    archetype_description = models.TextField(verbose_name = "Описание архетипа")  # Текст вопроса

    def __str__(self):
        return self.archetype_name
    
    class Meta:
         verbose_name = "Архетип"
         verbose_name_plural = "Архетипы"

# Модель пользователей
class User(models.Model):
    user_id = models.IntegerField(verbose_name = "ID пользователя в телеграм")
    user_name = models.CharField(max_length=255, verbose_name = "Имя пользователя", null=True)
    archetype = models.ForeignKey(Archetype, verbose_name = "Архетип пользователя", on_delete=models.CASCADE, related_name = "user_arch", null=True)  # Архетип первого пользователя
    signup_date = models.DateTimeField(auto_now=True, verbose_name = "Дата регистрации пользователя")
    free_limits = models.IntegerField(verbose_name = "Бесплатные запросы", null=True)
    payed_limits = models.IntegerField(verbose_name = "Оплаченные запросы", null=True)

    def __str__(self):
        return f"Пользователь {self.user_name}"

    class Meta:
         verbose_name = "Пользователь"
         verbose_name_plural = "Пользователи"


# Модель подписок
class Subscribe(models.Model):
    user_id = models.IntegerField(verbose_name = "ID пользователя")
    user_name = models.CharField(max_length=255, verbose_name = "Имя пользователя", null=True)
    start_date = models.DateTimeField(auto_now=True, verbose_name = "Дата начала подписки")
    end_date = models.DateTimeField(auto_now=True, verbose_name = "Дата завершения подписки")


    class Meta:
         verbose_name = "Подписка"
         verbose_name_plural = "Подписки"


# Модель Тесты
class Test(models.Model):
    user_id = models.IntegerField(verbose_name = "ID пользователя")  # ID пользователя
    date_time = models.DateTimeField(auto_now=True, verbose_name = "Дата начала теста")  # Дата и время, auto_now=True автоматически заполняет текущей датой и временем
    status = models.CharField(max_length=10, verbose_name = "Статус теста", choices=[('completed', 'Завершен'), ('pending', 'В процессе')])  # Статус теста
    first_user = models.ForeignKey(User, verbose_name = "ID пригласившего пользователя", on_delete=models.CASCADE, related_name = "user_arch", null=True)  # Архетип первого пользователя

    def __str__(self):
        return f"Тест ({self.status})"
    
    class Meta:
         verbose_name = "Тест"
         verbose_name_plural = "Тесты"



# Модель Совместимость
class Сompatibility(models.Model):
    first_arch = models.ForeignKey(Archetype, verbose_name = "Первый архетип", on_delete=models.CASCADE, related_name = "first_arch_compat")  # Архетип первого пользователя
    second_arch = models.ForeignKey(Archetype, verbose_name = "Второй архетип", on_delete=models.CASCADE, related_name = "second_arch_compat")  # Архетип второго пользователя
    first_user_description = models.TextField(verbose_name = "Отчет о совместимости для первого пользователя")  # Отчет о совместимости для первого пользователя

    def __str__(self):
        return f"Совместимость архетипов \"{self.first_arch.archetype_name}\" и \"{self.second_arch.archetype_name}\""
    
    class Meta:
         verbose_name = "Совместимость"
         verbose_name_plural = "Совместимость архетипов"



# Модель Вопросы
class Question(models.Model):
    text = models.TextField(verbose_name = "Текст вопроса")  # Текст вопроса
    order = models.PositiveIntegerField(verbose_name = "Порядковый номер вопроса")  # Порядковый номер вопроса

    def __str__(self):
        return f"Вопрос {self.order}: {self.text}"
    
    class Meta:
         verbose_name = "Вопрос"
         verbose_name_plural = "Вопросы"



# Модель Варианты ответа
class Answer(models.Model):
    text = models.CharField(max_length=555, verbose_name = "Текст варианта ответа")  # Текст варианта ответа
    question = models.ForeignKey(Question, verbose_name = "Вопрос", on_delete=models.CASCADE, related_name = "answer_question")  # Связь с вопросом
    first_arch_id = models.ForeignKey(Archetype, verbose_name = "Первый ахретип", on_delete=models.CASCADE, related_name = "first_arch_answer")  # Архетип первого пользователя
    second_arch_id = models.ForeignKey(Archetype, verbose_name = "Второй ахретип", on_delete=models.CASCADE, related_name = "second_arch_answer")  # Архетип второго пользователя
    answer_image = models.ImageField(blank=True, upload_to='images', verbose_name = "Изображение к варианту ответа")

    def __str__(self):
        return f"Вариант ответа: {self.text} на вопрос {self.question.text}"
    
    class Meta:
         verbose_name = "Вариант ответа"
         verbose_name_plural = "Варианты ответов"


    def image_tag(self):
        if self.answer_image.url is not None:
            return mark_safe('<img src="{}" height="60"/>'.format(self.answer_image.url))
        else:
            return ""

    image_tag.short_description = 'Превью'



# Модель для хранения результатов ответа в тесте
class Test_process(models.Model):
    test_id = models.ForeignKey(Test, verbose_name = "Тест", on_delete=models.CASCADE, related_name = "test_id_process")  # Тест
    question_id = models.ForeignKey(Question, verbose_name = "Вопрос", on_delete=models.CASCADE, related_name = "question_process")  # Связь с вопросом
    answer_id = models.ForeignKey(Answer, verbose_name = "Ответ", on_delete=models.CASCADE, related_name = "answer_process")  # Связь с ответом
    first_arch_id = models.ForeignKey(Archetype, verbose_name = "Архетип первого пользователя", on_delete=models.CASCADE, related_name = "first_arch_process")  # Архетип первого пользователя
    second_arch_id = models.ForeignKey(Archetype, verbose_name = "Архетип второго пользователя", on_delete=models.CASCADE, related_name = "second_arch_process")  # Архетип второго пользователя

    # def __str__(self):
    #     return f"Вариант ответа: {self.text} ({self.points} баллов)"
    
    class Meta:
         verbose_name = "Ответы теста"
         verbose_name_plural = "Ответы теста"


# Модель для хранения результатов ответа в тесте
class Related_user(models.Model):
    first_user_id = models.IntegerField(verbose_name = "ID первого пользователя")  # Отчет о совместимости для первого пользователя
    second_user_id = models.IntegerField(verbose_name = "ID второго пользователя")  # Отчет о совместимости для первого пользователя

    # def __str__(self):
    #     return f"Вариант ответа: {self.text} ({self.points} баллов)"
    
    class Meta:
         verbose_name = "Модель связанных пользователей"
         verbose_name_plural = "Модель связанных пользователей"



# Модель настроек
# class Settings(models.Model):
#     start_message = models.TextField(verbose_name = "Приветственное сообщение для команды /start")
#     help_message = models.TextField(verbose_name = "Сообщение для команды /help")
#     default_free_limits = models.PositiveIntegerField(verbose_name = "Количество бесплатных тестов для новых пользователей")
#     default_compatibilities = models.PositiveIntegerField(verbose_name = "Количество бесплатных проверок совместимостей для новых пользователей")
#     compat_price = models.PositiveIntegerField(verbose_name = "Цена разовой проверки совместимости (руб.)")
#     subscribe_price = models.PositiveIntegerField(verbose_name = "Цена ежемесячной подписки (руб.)")


#     class Meta:
#          verbose_name = "Настройки"
#          verbose_name_plural = "Настройки"





class promoCode(models.Model):

    codeName = models.CharField(max_length = 1000, verbose_name = "Название промокода", null=False)
    userId = models.IntegerField(verbose_name = "ID пользователя", null=True)
    limits = models.IntegerField(verbose_name = "Количество запросов", null=False)
    isActive = models.BooleanField(null=False, default=False, verbose_name = "Активен")
    activationDate = models.DateTimeField(auto_now_add=False, null=True)

    def __str__(self):
        return "%s" % (self.codeName)

    class Meta:
         verbose_name = "Промо-код"
         verbose_name_plural = "Промо-коды"

    REQUIRED_FIELDS = ['codeName', 'limits']