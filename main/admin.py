from django.contrib import admin
from .models import Test, Question, Archetype, Сompatibility, Answer, Test_process, promoCode, Settings
from django.contrib.auth.models import Group, User
from flatblocks.admin import FlatBlockAdmin
from flatblocks.models import FlatBlock


class SettingsFlatBlockAdmin(FlatBlockAdmin):
    # Поля, которые будут отображаться в списке блоков в админ-панели
    list_display = ('compat_price', 'subscribe_price')
    
    

# Отменяем регистрацию стандартного FlatBlockAdmin
admin.site.unregister(FlatBlock)

# Регистрируем вашу кастомную модель с административным представлением
admin.site.register(Settings, SettingsFlatBlockAdmin)

# Регистрация модели Test в административной панели
# admin.site.register(Test, 
#     list_display=('user', 'date_time', 'status'),
#     list_filter=('status', ),
#     search_fields=('user__username', 'date_time'),
#     date_hierarchy='date_time'
# )

# Регистрация нужных моделей в админке
admin.site.register(Archetype)
admin.site.register(Сompatibility)
# admin.site.register(Answer)
# admin.site.register(Test_process)

# Создаем inline
class QuestionAnswerInline(admin.TabularInline):
    model = Answer
    readonly_fields = ('id', 'image_tag',)
    # list_display = ('text', 'question', 'first_arch_id', 'second_arch_id', 'image_tag')
    extra = 6


class QuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionAnswerInline]
    list_display = ('text', 'order')


class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('codeName', 'limits', 'isActive')

    # Определите, какие поля вы хотите видеть при редактировании исключительно
    fields = ('codeName', 'limits', 'isActive')

    # Если вам нужно исключить какие-либо поля, используйте `exclude`
    # exclude = ('userId', 'activationDate')

    search_fields = ('codeName',)
    list_filter = ('isActive',)

admin.site.register(promoCode, PromoCodeAdmin)
admin.site.register(Question, QuestionAdmin)

admin.site.unregister(Group)
admin.site.unregister(User)

admin.site.site_header = "Архип. Административная панель"